import argparse
import errno
import json
import os
import os.path as op
import shutil
import sys


def progress_bar(iteration, total, bar_length=50):
    percent = int(round((iteration / total) * 100))
    nb_bar_fill = int(round((bar_length * percent)/100))
    bar_fill = '#' * nb_bar_fill
    bar_empty = ' ' * (bar_length - nb_bar_fill)
    sys.stdout.write("\r[%s] %s%%" % (str(bar_fill + bar_empty), percent))
    sys.stdout.flush()


def mkdir(path):
    # if it is the current folder, skip.
    # otherwise the original code will raise FileNotFoundError
    if path == "":
        return
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def tsv_writer(values, tsv_file_name, sep="\t"):
    mkdir(op.dirname(tsv_file_name))
    idx = 0
    tsv_file_name_tmp = tsv_file_name + ".tmp"
    with open(tsv_file_name_tmp, "w") as fp:
        assert values is not None
        for value in values:
            assert value is not None
            # this step makes sure python2 and python3 encoded img string are the same.
            # for python2 encoded image string, it is a str class starts with "/".
            # for python3 encoded image string, it is a bytes class starts with "b'/".
            # v.decode('utf-8') converts bytes to str so the content is the same.
            # v.decode('utf-8') should only be applied to bytes class type.
            value = [
                v if not isinstance(v, bytes) else v.decode("utf-8") for v in value
            ]
            v = "{0}\n".format(sep.join(map(str, value)))
            fp.write(v)
            idx = idx + len(v)
    os.rename(tsv_file_name_tmp, tsv_file_name)


def create_anno_tsv_from_vcr(args):
    label_rows = []
    with open(args.anno_path, "rb") as fid:
        data = json.load(fid)
        if args.max_nums > 0:
            data = data[:args.max_nums]
        total = len(data)
        for i, row in enumerate(data):
            progress_bar(i+1, total)
            img_id = row['id']
            img_path = row['image_path'].replace(args.orig_data_path, args.data_path)
            if not op.isfile(img_path):
                destination_dir = op.dirname(img_path)
                os.makedirs(destination_dir, exist_ok=True)
                shutil.copy(row['image_path'], img_path)
            caption = json.dumps({key: val for key, val in row.items() if key in ["prompt", "targets", "prediction"]})
            accuracy = str(row['metrics']['vqa_accuracy'])
            label_rows.append(
                [
                    img_id+":"+caption,
                    accuracy,
                    img_path,
                ]
            )

    file_name = op.basename(args.anno_path).replace(".json", ".tsv")
    label_file = os.path.join(args.output_path, file_name)
    tsv_writer(label_rows, label_file)


def create_anno_tsv_from_llama3v_json(args):
    # args.anno_path = '/checkpoint/onevision/xlformer_assets/datasets/grounding/evals/vcr_qar/vcr.json'
    # args.orig_data_path = "/checkpoint/onevision/xlformer_assets/datasets/grounding/evals/vcr_qar"
    # args.data_path = "/home/pengchuanzhang/rsc/tsvviewer/data/images/grounding/evals/vcr_qar"
    # args.output_path = "/home/pengchuanzhang/rsc/tsvviewer/data/vcr_direct/vcr_qar_eval"
    label_rows = []
    with open(args.anno_path, "rb") as fid:
        data = json.load(fid)
        if args.max_nums > 0:
            data = data[:args.max_nums]
        total = len(data)
        for i, row in enumerate(data):
            progress_bar(i+1, total)
            img_id = row['id']
            orig_image_path = os.path.join(args.orig_data_path, row['image'])
            img_path = os.path.join(args.data_path, row['image'])
            if not op.isfile(img_path):
                destination_dir = op.dirname(img_path)
                os.makedirs(destination_dir, exist_ok=True)
                shutil.copy(orig_image_path, img_path)
            caption = json.dumps(row["conversation"])
            anns = [
                {
                    "caption": caption,
                }
            ]
            label_rows.append(
                [
                    img_id,
                    json.dumps(anns),
                    img_path,
                ]
            )

    file_name = op.basename(args.anno_path).replace(".json", ".tsv")
    label_file = os.path.join(args.output_path, file_name)
    tsv_writer(label_rows, label_file)


def create_anno_tsv_from_llama3v_compare(args):
    # args.anno_path = '/home/pengchuanzhang/tmp/mm-0011-sft-regioncaption-pengchuanzhang-f5xdr2/2024_04_18_llama3v_checkpoint_0024000/raw_results_as_core_eval-llama3v.json'
    label_rows = []
    miss_flist = []
    with open(args.anno_path, "rb") as fid:
        data = json.load(fid)
        if args.max_nums > 0:
            data = data[:args.max_nums]
        total = len(data)
        for i, row in enumerate(data):
            progress_bar(i+1, total)
            img_id = "_".join(map(str, row['id']))
            img_path = row['image_path']
            if not op.isfile(img_path):
                miss_flist.append(img_path)
                continue
            caption = json.dumps({key: val for key, val in row.items() if key in ["prompt", "targets", "prediction"]})
            anns = [
                {
                    "caption": caption,
                }
            ]
            label_rows.append(
                [
                    img_id,
                    json.dumps(anns),
                    img_path,
                ]
            )

    file_name = op.basename(args.anno_path).replace(".json", ".tsv")
    label_file = os.path.join(args.output_path, file_name)
    tsv_writer(label_rows, label_file)
    with open(os.path.join(args.output_path, "missing_flist.txt"), "w") as fid:
        fid.write("\n".join(miss_flist))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create Task Eval tsv dataset")
    parser.add_argument(
        "--anno_path",
        default="/checkpoint/onevision/xldumps_mm/kalyanv/013_1xacad_1xvip_17b_l2_sweep_lr_min_ratio_mcq_full_learn.yaml/kalyanv/013_1xacad_1xvip_17b_l2_sweep_lr_min_ratio_mcq_full_learn.yaml_run006/evals/2024_03_26_nextgen-v2_checkpoint_0022000/raw_results_vcr_rsc-nextgen-v2.json",
        help="path to Task Eval annotation data",
    )
    parser.add_argument(
        "--orig_data_path",
        default="/checkpoint/onevision/xlformer_assets/datasets/grounding/vcr_eval_multichoice/vcr/vcr1images",
        help="path to Task Eval image data",
    )
    parser.add_argument(
        "--data_path",
        default="/home/pengchuanzhang/rsc/tsvviewer/data/images/013_1xacad_1xvip_17b_l2_sweep_lr_min_ratio_mcq_full_learn.yaml_run006/vcr1images",
        help="path to Task Eval image data",
    )
    parser.add_argument(
        "--output_path",
        default="/home/pengchuanzhang/rsc/tsvviewer/data/013_1xacad_1xvip_17b_l2_sweep_lr_min_ratio_mcq_full_learn.yaml_run006",
        help="path where to save the resulting tsv files",
    )
    parser.add_argument(
        "--data_type",
        default="vcr",
        help="coco_json, imagelist_json, omnilabel_json",
    )
    parser.add_argument("--max_nums", type=int, default=-1)
    args = parser.parse_args()
    print(args)
    if args.data_type == "vcr":
        create_anno_tsv_from_vcr(args)
    elif args.data_type == "llama3v_json":
        create_anno_tsv_from_llama3v_json(args)
    elif args.data_type == "llama3v_compare":
        create_anno_tsv_from_llama3v_compare(args)
