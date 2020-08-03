import os
import os.path as op
import logging
import yaml
import errno
from tqdm import tqdm
from collections import OrderedDict


def list_all_data(data_dir):
    return sorted([d for d in os.listdir(data_dir) if not d.startswith('.')])


def ensure_directory(path):
    if path == '' or path == '.':
        return
    if path is not None and len(path) > 0:
        if not op.exists(path) and not op.islink(path):
            os.makedirs(path)


def write_to_file(contxt, file_name):
    p = os.path.dirname(file_name)
    ensure_directory(p)
    with open(file_name, 'w') as fp:
        fp.write(contxt)


def generate_lineidx(filein, idxout=None, replace_existing=False):
    if not idxout:
        idxout = op.splitext(filein)[0] + '.lineidx'
    logger = logging.getLogger(__name__)
    if op.isfile(idxout) and not replace_existing:
        logger.info("{} file exist and return".format(idxout))
        return
    if op.isfile(idxout) and replace_existing:
        logger.info("overwrite lineidx file: {}".format(idxout))
    with open(filein,'r') as fpin, open(idxout,'w') as fpout:
        fsize = os.fstat(fpin.fileno()).st_size
        def gen_rows():
            fpos = 0
            while fpos!=fsize:
                yield str(fpos)
                fpin.readline()
                fpos = fpin.tell()
        with tqdm(total=fsize) as t:
            for row in gen_rows():
                t.update(int(row) - t.n)
                fpout.write(row+"\n")


def load_labelmap_file(labelmap_file):
    label_dict = None
    if labelmap_file is not None and op.isfile(labelmap_file):
        label_dict = OrderedDict()
        with open(labelmap_file, 'r') as fp:
            for line in fp:
                label = line.strip().split('\t')[0]
                if label in label_dict:
                    raise ValueError("Duplicate label " + label + " in labelmap.")
                else:
                    label_dict[label] = len(label_dict)
    return label_dict


def load_linelist_file(linelist_file):
    if linelist_file is not None:
        with open(linelist_file, 'r') as fp:
            return [int(line.strip()) for line in fp]


def load_from_yaml_file(yaml_file):
    with open(yaml_file, 'r') as fp:
        return yaml.load(fp, Loader=yaml.CLoader)


def find_file_path_in_yaml(fname, root):
    if fname is not None:
        if op.isfile(fname):
            return fname
        elif op.isfile(op.join(root, fname)):
            return op.join(root, fname)
        else:
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), op.join(root, fname)
            )
