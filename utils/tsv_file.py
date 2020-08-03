import os
import os.path as op
import json
import logging
from tqdm import tqdm
import multiprocessing
from pathos.multiprocessing import ProcessingPool as Pool

# add parent path to make this script alone runnable
import sys
sys.path.append(op.dirname(op.dirname(op.realpath(__file__))))

from utils.file_io import ensure_directory, generate_lineidx
from utils.image_io import img_from_base64


class TSVFile(object):
    def __init__(self, tsv_file):
        self.tsv_file = tsv_file
        self.lineidx = op.splitext(tsv_file)[0] + '.lineidx' 
        self._fp = None
        self._lineidx = None
        self.__ensure_lineidx_loaded()
    
    def num_rows(self):
        return len(self._lineidx) 

    def seek(self, idx):
        self.__ensure_tsv_opened()
        pos = self._lineidx[idx]
        self._fp.seek(pos)
        return [s.strip() for s in self._fp.readline().split('\t')]

    def rows(self, filter_idx=None):
        if filter_idx is None:
            filter_idx = range(self.num_rows())
        for idx in filter_idx:
            yield self.seek(idx)

    def __ensure_lineidx_loaded(self):
        logger = logging.getLogger(__name__)
        if self._lineidx is None:
            if not op.isfile(self.lineidx):
                if self.generate_lineidx:
                    logger.warning("Generating lineidx file because it does not exist. " \
                        "Note this might cause problem in distributed training." \
                        "It is better to check lineidx files before training.")
                    generate_lineidx(self.tsv_file, self.lineidx)
                else:
                    raise ValueError("{} file does not exist".format(self.lineidx)) 

            with open(self.lineidx, 'r') as fp:
                self._lineidx = [int(i.strip()) for i in fp.readlines()]

    def __ensure_tsv_opened(self):
        if self._fp is None:
            self._fp = open(self.tsv_file, 'r')

    @staticmethod
    def __guess_col_image(tsv_file):
        # peek one line to find the longest column as col_image
        cols = next(TSVFile.reader(tsv_file))
        return max(enumerate(cols), key=lambda x: len(x[1]))[0]

    @staticmethod
    def __is_label_json_format(label_file):
        cols = next(TSVFile.reader(label_file))
        label = cols[1].strip()
        return label.startswith('{') or label.startswith('[')

    @staticmethod
    def parse_annotation(str):
        results = {}
        if str.startswith('{') or str.startswith('['):
            json_result = json.loads(str)
            if isinstance(json_result, list):
                results['objects'] = json_result
            else:
                assert 'objects' in json_result
                results = json_result
        else:
            rects = []
            for l in str.replace(',', ';').split(';'):
                kv = [x.strip() for x in l.split(':')]
                if (len(kv) == 1):
                    rects.append({'class':kv[0]})
                else:
                    rects.append({'class':kv[0], 'conf':float(kv[1])})
            results['objects'] = rects
        return results

    @staticmethod
    def reader(tsv_file_name, sep='\t'):
        with open(tsv_file_name, 'r') as fp:
            for _, line in enumerate(fp):
                yield [x.strip() for x in line.split(sep)]

    @staticmethod
    def writer(tsv_file_name, values, sep='\t'):
        ensure_directory(op.dirname(tsv_file_name))
        tsv_file_name_tmp = tsv_file_name + '.tmp'
        import sys
        is_py2 = sys.version_info.major == 2
        with open(tsv_file_name_tmp, 'wb') as fp:
            assert values is not None
            for value in values:
                assert value
                if is_py2:
                    v = sep.join(map(lambda v: v.encode('utf-8') if isinstance(v, unicode) else str(v), value)) + '\n'
                else:
                    v = sep.join(map(lambda v: v.decode() if type(v) == bytes else str(v), value)) + '\n'
                    v = v.encode()
                fp.write(v)
        os.rename(tsv_file_name_tmp, tsv_file_name)

    @staticmethod
    def writer_with_lineidx(tsv_file_name, values, sep='\t'):
        ensure_directory(op.dirname(tsv_file_name))
        tsv_lineidx_file = op.splitext(tsv_file_name)[0] + '.lineidx'
        idx = 0
        tsv_file_name_tmp = tsv_file_name + '.tmp'
        tsv_lineidx_file_tmp = tsv_lineidx_file + '.tmp'
        import sys
        is_py2 = sys.version_info.major == 2
        with open(tsv_file_name_tmp, 'wb') as fp, open(tsv_lineidx_file_tmp, 'w') as fpidx:
            assert values is not None
            for value in values:
                assert value
                if is_py2:
                    v = sep.join(map(lambda v: v.encode('utf-8') if isinstance(v, unicode) else str(v), value)) + '\n'
                else:
                    v = sep.join(map(lambda v: v.decode() if type(v) == bytes else str(v), value)) + '\n'
                    v = v.encode()
                fp.write(v)
                fpidx.write(str(idx) + '\n')
                idx = idx + len(v)
        os.rename(tsv_file_name_tmp, tsv_file_name)
        os.rename(tsv_lineidx_file_tmp, tsv_lineidx_file)

    @staticmethod
    def __ensure_lineidx(tsv_file):
        assert op.isfile(tsv_file)
        lineidx_file = op.splitext(tsv_file)[0] + '.lineidx'
        if not op.isfile(lineidx_file) or op.getmtime(lineidx_file) < op.getmtime(tsv_file):
            logging.info('generating lineidx file: {}'.format(lineidx_file))
            generate_lineidx(tsv_file, lineidx_file, replace_existing=True)

    @staticmethod
    def __ensure_separate_label(full_tsv, label_file):
        if op.isfile(label_file) or op.islink(label_file):
            return

        num_rows = TSVFile(full_tsv).num_rows()
        logging.info('generating label file: {}'.format(label_file))
        def gen_rows():
            for row in tqdm(TSVFile.reader(full_tsv), total=num_rows):
                yield row[0:2]
        TSVFile.writer(label_file, gen_rows())

    @staticmethod
    def __ensure_labelmap(label_file, labelmap_file):
        """ A label file always has two columns: key, label
        """
        if op.isfile(labelmap_file) or op.islink(labelmap_file):
            return

        logging.info('generating labelmap file: {}'.format(labelmap_file))

        labelmap = []
        num_rows = TSVFile(label_file).num_rows()
        for cols in tqdm(TSVFile.reader(label_file), total=num_rows):
            rects = TSVFile.parse_annotation(cols[1])['objects']
            labels = [rect['class'] for rect in rects if 'class' in rect]
            labels = set(filter(lambda x: not x.startswith('-'), labels))
            labelmap.extend(labels)

        if len(labelmap) == 0:
            logging.warning('there are no labels!')
        labelmap = sorted(list(set(labelmap)))
        logging.info('find {} labels'.format(len(labelmap)))
        TSVFile.writer(labelmap_file, map(lambda x: [x,], labelmap))

    @staticmethod
    def __ensure_hw_file(tsv_file, hw_file):
        if op.isfile(hw_file) or op.islink(hw_file):
            return

        logging.info('generating hw file: {}'.format(hw_file))
        col_image = TSVFile.__guess_col_image(tsv_file)
        num_images = TSVFile(tsv_file).num_rows()

        num_worker = multiprocessing.cpu_count() * 2
        num_tasks = num_worker * 5
        num_image_per_task = (num_images + num_tasks - 1) // num_tasks
        multi_thread = True if num_images > 5 else False
        if not multi_thread:
            rows = TSVFile.reader(tsv_file)
            def gen_rows():
                for row in tqdm(rows, total=num_images):
                    yield row[0], ' '.join(map(str, img_from_base64(row[col_image]).shape[:2]))
            TSVFile.writer(hw_file, gen_rows())
        else:
            logging.info('multiprocessing with {} workers and {} tasks, with each task processing {} images'
                .format(num_worker, num_tasks, num_image_per_task))
            with Pool(num_worker) as pool:
                def get_hw(task_id):
                    idx_start = task_id * num_image_per_task
                    idx_end = min(idx_start + num_image_per_task, num_images)
                    rows = TSVFile(tsv_file).rows(filter_idx=range(idx_start, idx_end))
                    return [(row[0], ' '.join(map(str, img_from_base64(row[col_image]).shape[:2])))
                        for row in rows]
                all_result = list(tqdm(pool.imap(get_hw, range(num_tasks)), total=num_tasks))
            x = []
            for r in all_result:
                x.extend(r)
            TSVFile.writer(hw_file, x)

    @staticmethod
    def __ensure_inverted_label_file(label_file, inverted_file):
        if op.isfile(inverted_file) or op.islink(inverted_file):
            return

        logging.info('generating inverted label file: {}'.format(inverted_file))

        inverted = {}
        total = 0
        num_rows = TSVFile(label_file).num_rows()
        for i, cols in tqdm(enumerate(TSVFile.reader(label_file)), total=num_rows):
            rects = TSVFile.parse_annotation(cols[1])['objects']
            labels = [rect['class'] for rect in rects if 'class' in rect]
            labels = set(filter(lambda x: not x.startswith('-'), labels))

            for l in labels:
                if l not in inverted:
                    inverted[l] = [i]
                else:
                    inverted[l].append(i)
            total += 1
        
        def gen_inverted_rows(inv):
            # sort inverted list by the length of each list
            for x in sorted(inv.items(), key=lambda x: len(x[1]), reverse=True):
                yield x[0], ' '.join(map(str, x[1]))
        TSVFile.writer(inverted_file, gen_inverted_rows(inverted))

    @staticmethod
    def ensure_metainfo(tsv_file, label_file=None, prediction_file=None, labelmap_file=None, hw_file=None):
        """ Check and ensure meta info for visualization
            The meta info includes: 
            1. lineidx for the input tsv
            2. a separate label file and a lineidx file
            3. labelmap file
            4. hw file
            5. inverted label file
            6. optional prediction file and its lineidx file
        """
        assert op.isfile(tsv_file)

        # check and generate lineidx if needed
        TSVFile.__ensure_lineidx(tsv_file)

        # check and generate label file and lineidx if needed
        if label_file is None:
            label_file = op.splitext(tsv_file)[0] + '.label.tsv'
        TSVFile.__ensure_separate_label(tsv_file, label_file)
        TSVFile.__ensure_lineidx(label_file)

        # generate lineidx for prediction file if needed
        if prediction_file is not None:
            TSVFile.__ensure_lineidx(prediction_file)

        # check and generate labelmap if needed
        if labelmap_file is None:
            labelmap_file = op.splitext(tsv_file)[0] + '.labelmap.txt'
        TSVFile.__ensure_labelmap(label_file, labelmap_file)

        # check and generate hw file if needed
        #### not used and comment fow now.
        # if hw_file is None:
        #     hw_file = op.splitext(tsv_file)[0] + '.hw.tsv'
        # TSVFile.__ensure_hw_file(tsv_file, hw_file)
            
        # check and generate inverted label file if needed
        inverted_file = op.splitext(label_file)[0] + '.inverted.tsv'
        TSVFile.__ensure_inverted_label_file(label_file, inverted_file)


if __name__ == "__main__":
    import logger
    import argparse

    parser = argparse.ArgumentParser(description='Test tsv file utilities')
    parser.add_argument('tsv', action="store")
    args = parser.parse_args()

    logger.init_logging()
    TSVFile.ensure_metainfo(args.tsv)