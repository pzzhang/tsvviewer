import cv2
import json
from PIL import Image
import os
import os.path as op

# add parent path to make this script alone runnable
import sys
sys.path.append(op.dirname(op.dirname(op.realpath(__file__))))

from utils.tsv_file import TSVFile
from utils.file_io import load_linelist_file, load_from_yaml_file
from utils.file_io import find_file_path_in_yaml
from utils.image_io import img_from_base64


class TSVDataset(object):
    def __init__(self, img_file, label_file=None, hw_file=None, linelist_file=None):
        """Constructor.
        Args:
            img_file: Image file with image key and base64 encoded image str.
            label_file: An optional label file with image key and label information. 
                A label_file is required for training and optional for testing.
            hw_file: An optional file with image key and image height/width info.
            linelist_file: An optional file with a list of line indexes to load samples.
                It is useful to select a subset of samples or duplicate samples. 
        """
        assert label_file is not None

        self.img_file = img_file
        self.label_file = label_file
        self.hw_file = hw_file
        self.linelist_file = linelist_file

        self.img_tsv = TSVFile(img_file)
        self.label_tsv = None if label_file is None else TSVFile(label_file)
        self.hw_tsv = None if hw_file is None else TSVFile(hw_file)
        self.line_list = load_linelist_file(linelist_file)

    def __len__(self):
        if self.line_list is None:
            return self.img_tsv.num_rows() 
        else:
            return len(self.line_list)

    def __getitem__(self, idx):
        img = self.get_image(idx)
        annotations = self.get_annotations(idx)
        target = self.get_target_from_annotations(annotations, img.size, idx)
        img, target = self.apply_transforms(img, target)
        return img, target, idx

    def get_line_no(self, idx):
        return idx if self.line_list is None else self.line_list[idx]

    def get_image(self, idx): 
        line_no = self.get_line_no(idx)
        row = self.img_tsv.seek(line_no)
        # use -1 to support old format with multiple columns.
        cv2_im = img_from_base64(row[-1])
        cv2_im = cv2.cvtColor(cv2_im, cv2.COLOR_BGR2RGB)
        # convert to PIL Image as required by transforms
        img = Image.fromarray(cv2_im)
        return img       

    def get_annotations(self, idx):
        line_no = self.get_line_no(idx)
        if self.label_tsv is not None:
            row = self.label_tsv.seek(line_no)
            annotations = json.loads(row[1])
            return annotations
        else:
            return []

    def get_target_from_annotations(self, annotations, img_size, idx):
        # This function will be overwritten by each dataset to 
        # decode the labels to specific formats for each task. 
        return annotations

    def apply_transforms(self, image, target=None):
        # This function will be overwritten by each dataset to 
        # apply transforms to image and targets.
        return image, target

    def get_img_info(self, idx):
        if self.hw_tsv is not None:
            line_no = self.get_line_no(idx)
            row = self.hw_tsv.seek(line_no)
            try:
                # json string format with "height" and "width" being the keys
                return json.loads(row[1])[0]
            except ValueError:
                # list of strings representing height and width in order
                hw_str = row[1].split(' ')
                hw_dict = {"height": int(hw_str[0]), "width": int(hw_str[1])}
                return hw_dict

    def get_img_key(self, idx):
        line_no = self.get_line_no(idx)
        # based on the overhead of reading each row.
        if self.hw_tsv:
            return self.hw_tsv.seek(line_no)[0]
        elif self.label_tsv:
            return self.label_tsv.seek(line_no)[0]
        else:
            return self.img_tsv.seek(line_no)[0]

    @staticmethod
    def load_inverted_index(inverted_file, min_inverted_list_length=0, max_inverted_rows=-1):
        def gen_rows():
            num_rows = 0
            for row in TSVFile.reader(inverted_file):
                inv_list = row[1].split(' ')
                if len(inv_list) < min_inverted_list_length:
                    continue
                num_rows += 1
                yield row[0], list(map(int, inv_list))
                if max_inverted_rows >= 0 and num_rows >= max_inverted_rows:
                    break
        return {x[0]: x[1] for x in gen_rows()}


class TSVYamlDataset(TSVDataset):
    """ TSVDataset taking a Yaml file for easy function call
    """
    def __init__(self, yaml_file):
        self.cfg = load_from_yaml_file(yaml_file)
        self.root = op.dirname(yaml_file)
        img_file = find_file_path_in_yaml(self.cfg['img'], self.root)
        label_file = find_file_path_in_yaml(self.cfg.get('label', None),
                                            self.root)
        hw_file = find_file_path_in_yaml(self.cfg.get('hw', None), self.root)
        linelist_file = find_file_path_in_yaml(self.cfg.get('linelist', None),
                                               self.root)

        super(TSVYamlDataset, self).__init__(
            img_file, label_file, hw_file, linelist_file)


class TSVSubset(object):
    def __init__(self, name, tsv_file, label_file=None, prediction_file=None, labelmap_file=None, 
                 hw_file=None, min_inverted_list_length=0, max_inverted_rows=-1, version=0):
        self.name = name
        self.tsv_file = tsv_file
        self.label_file = label_file if label_file is not None else op.splitext(tsv_file)[0] + '.label.tsv'
        self.prediction_file = prediction_file  # prediction file could be optional as None
        self.labelmap_file = labelmap_file if labelmap_file is not None else op.splitext(self.label_file)[0] + '.labelmap.txt'
        self.hw_file = hw_file if hw_file is not None else op.splitext(tsv_file)[0] + '.hw.tsv'
        self.inverted_file = op.splitext(self.label_file)[0] + '.inverted.tsv'
        self.min_inverted_list_length = min_inverted_list_length
        self.max_inverted_rows = max_inverted_rows
        self.version = version

    @classmethod
    def from_singlefile(cls, name, tsv_file, version=0):
        if version == 0:
            return cls(name, tsv_file, version=version)
        else:
            label_file = op.splitext(tsv_file)[0] + '.label.v{}.tsv'.format(version)
            if op.isfile(label_file):
                return cls(name, tsv_file, label_file, version=version)

    @classmethod
    def from_yaml(cls, name, yaml_file):
        cfg = load_from_yaml_file(yaml_file)
        if cfg.get('img', None) is None:
            return None
        root = op.dirname(yaml_file)
        subset = cls(name,
            tsv_file=find_file_path_in_yaml(cfg['img'], root),
            label_file=find_file_path_in_yaml(cfg.get('label', None), root),
            prediction_file=find_file_path_in_yaml(cfg.get('prediction', None), root),
            labelmap_file=find_file_path_in_yaml(cfg.get('labelmap', None), root),
            min_inverted_list_length=cfg.get('min_inverted_list_length', 0),
            max_inverted_rows=cfg.get('max_inverted_rows', -1)
            # hw_file=find_file_path_in_yaml(cfg.get('hw', None), root)
        )
        return subset
        
    @classmethod
    def from_name(cls, data_dir, subset_name, version=0):
        if subset_name.endswith('.yaml'):
            subset = TSVSubset.from_yaml(subset_name, op.join(data_dir, subset_name))
        else:
            subset = TSVSubset.from_singlefile(subset_name, op.join(data_dir, subset_name) + '.tsv', version=version)
        return subset


def get_all_data_info(data_dir):
    subsets = []
    for yaml in [fn for fn in os.listdir(data_dir) if fn.endswith('.yaml')]:
        s = TSVSubset.from_yaml(yaml, op.join(data_dir, yaml))
        if s is not None:
            subsets.append(s)
    subsets = sorted(subsets, key=lambda x: x.name)
    for tsv in ['train', 'trainval', 'val', 'test']:
        tsv_file = op.join(data_dir, tsv) + '.tsv'
        if op.isfile(tsv_file):
            subsets.append(TSVSubset.from_singlefile(tsv, tsv_file, version=0))
        # check other label versions
        for ver in range(1, 1000000):
            s = TSVSubset.from_singlefile(tsv, tsv_file, version=ver)
            if s is None:
                break
            subsets.append(s)

    subsets_labels = []
    for s in subsets:
        if not op.isfile(s.tsv_file):
            continue
        TSVFile.ensure_metainfo(s.tsv_file, label_file=s.label_file, prediction_file=s.prediction_file, labelmap_file=s.labelmap_file, hw_file=s.hw_file)
        inverted = TSVDataset.load_inverted_index(s.inverted_file, 
                min_inverted_list_length=s.min_inverted_list_length, 
                max_inverted_rows=s.max_inverted_rows)
        label_count = [(k, len(v)) for k, v in inverted.items()]
        label_count = sorted(label_count, key=lambda x: x[1])
        subsets_labels.append((s.name, s.version, [(i, l, c) for i, (l, c) in enumerate(label_count)]))
    
    name_subset_labels = [(op.split(data_dir)[1], subsets_labels)]
    return name_subset_labels


if __name__ == "__main__":
    import logger
    import argparse

    parser = argparse.ArgumentParser(description='Test data info utilities')
    parser.add_argument('data_dir', action="store")
    args = parser.parse_args()

    logger.init_logging()
    get_all_data_info(args.data_dir)