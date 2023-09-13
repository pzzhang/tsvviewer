# -*- coding: utf-8 -*-
from django.http import HttpResponseRedirect, HttpResponse, FileResponse
from django.shortcuts import render
from django.urls import reverse
from django.core.cache import cache
import os.path as op
import logging
import json
import copy
import base64
from utils.logger import init_logging
from utils.file_io import list_all_data
from utils.tsv_file import TSVFile
from utils.tsv_dataset import TSVDataset, TSVSubset
from utils.tsv_dataset import get_all_data_info


init_logging()


def get_data_root():
    return op.join(op.dirname(op.dirname(op.realpath(__file__))), 'data')


def list_data(request):
    names = list_all_data(get_data_root())
    context = {'names': names}
    return render(request, 'detection/list_data.html', context)


def data_overview(request):
    data = request.GET.get('data')
    name_subsets_labels = get_all_data_info(op.join(get_data_root(), data))
    context = {'name_subsets_versions_labelcounts': name_subsets_labels}
    return render(request, 'detection/data_overview.html', context)


def show_image(request):
    data = request.GET.get('data')
    subset = request.GET.get('subset')
    version = int(request.GET.get('version'))
    idx = int(request.GET.get('imgidx'))
    tsv = cache.get(data+subset+str(version))
    if not tsv:
        logging.info('Cache miss. Load data to cache: {}/{}'.format(data, subset))
        s = TSVSubset.from_name(op.join(get_data_root(), data), subset, version=version)
        TSVFile.ensure_metainfo(s.tsv_file, label_file=s.label_file, prediction_file=s.prediction_file,
            labelmap_file=s.labelmap_file, hw_file=s.hw_file)
        tsv = TSVFile(s.tsv_file)
        cache.set(data+subset+str(version), tsv)

    row = tsv.seek(idx)
    if row[-1].startswith('http'):
        return HttpResponseRedirect(row[-1])
    if op.isfile(row[-1]):
        return FileResponse(open(row[-1], 'rb'))
    jpgbytestring = base64.b64decode(row[-1])
    return HttpResponse(jpgbytestring, content_type="image/jpeg")

def retrieve_images(label_file, inverted, prediction_file, label, start_id, min_conf=-float('inf'), max_conf=float('inf')):
    label_tsv = cache.get(op.abspath(label_file))
    if not label_tsv:
        label_tsv = TSVFile(label_file)
        cache.set(op.abspath(label_file), label_tsv)

    prediction_tsv = None
    if prediction_file is not None:
        prediction_tsv = cache.get(op.abspath(prediction_file))
        if not prediction_tsv:
            prediction_tsv = TSVFile(prediction_file)
            cache.set(op.abspath(prediction_file), prediction_tsv)

    if label is None:
        idx = list(range(label_tsv.num_rows()))
    else:
        assert label in inverted
        idx = inverted[label]
    if len(idx) == 0:
        return

    while start_id > len(idx):
        start_id = start_id - len(idx)
    while start_id < 0:
        start_id = start_id + len(idx)

    logging.info('start to read')

    def filter_rects(rects, min_conf, max_conf):
        rects = [r for r in rects if \
                r.get('conf', 1) >= min_conf and \
                r.get('conf', 1) <= max_conf]
        return rects

    for i in idx[start_id:]:
        row_label = label_tsv.seek(i)
        key = row_label[0]
        gt = TSVFile.parse_annotation(row_label[1])
        gt['objects'] = filter_rects(gt['objects'], min_conf, max_conf)
        pred = {'objects': []}
        if prediction_tsv:
            row_label = prediction_tsv.seek(i)
            pred = TSVFile.parse_annotation(row_label[1])
            pred['objects'] = filter_rects(pred['objects'], min_conf, max_conf)

        yield (key, i, gt, pred)


def view_image_js(request, data, subset, version, label, start_id, imKey=None, min_conf=None, max_image_shown=50):
    '''
    use js to render the box in the client side
    '''
    s = TSVSubset.from_name(op.join(get_data_root(), data), subset, version=version)
    TSVFile.ensure_metainfo(s.tsv_file, label_file=s.label_file, prediction_file=s.prediction_file,
        labelmap_file=s.labelmap_file, hw_file=s.hw_file)

    inverted = cache.get('inverted_' + s.tsv_file + s.label_file)
    if not inverted:
        logging.info('loading inverted index')
        inverted = TSVDataset.load_inverted_index(s.inverted_file, 
            min_inverted_list_length=s.min_inverted_list_length,
            max_inverted_rows=s.max_inverted_rows)
        cache.set('inverted_' + s.tsv_file + s.label_file, inverted)

    images = retrieve_images(s.label_file, inverted, s.prediction_file, label, start_id, min_conf=min_conf)

    label_count = [('any', TSVFile(s.tsv_file).num_rows())]
    for k, v in sorted(inverted.items(), key=lambda x: x[0]):
        label_count.append((k, len(v)))

    all_type_to_annotations, all_url, all_key = [], [], []
    for key, idx, gt, pred in images:
        if imKey is None or imKey in key:
            all_key.append(key)
            all_url.append(reverse('detection:showimage') + \
                '?data={}&subset={}&version={}&imgidx={}&key={}'.format(data, subset, version, idx, key))
            all_type_to_annotations.append({'gt': gt, 'pred': pred})
        if len(all_key) >= max_image_shown:
            break

    def nav_link(start_id):
        kwargs = copy.deepcopy(request.GET)
        kwargs['start_id'] = str(start_id)
        return reverse('detection:viewimages') + '?' + \
            '&'.join(['{}={}'.format(k, kwargs[k]) for k in kwargs])

    context = {'all_type_to_annotations': json.dumps(all_type_to_annotations),
               'all_url': json.dumps(all_url),
               'all_key': json.dumps(all_key),
               'previous_link': nav_link(max(0, start_id - max_image_shown)),
               'next_link': nav_link(start_id + len(all_type_to_annotations)),
               'black_list': '',
               'label_count' : json.dumps(label_count),
               }

    # precache to speedup show_image
    cache.set(data+subset+str(version), TSVFile(s.tsv_file))
    return render(request, 'detection/images_js2.html', context)


def view_images(request):
    data = request.GET.get('data')

    subset = request.GET.get('subset')
    if subset == 'None':
        subset = None

    key = request.GET.get('key')
    version = request.GET.get('version')
    if version == 'None':
        version = None
    version = int(version) if type(version) is str or \
        type(version) is unicode else version

    min_conf = request.GET.get('min_conf')
    min_conf = -1 if min_conf is None else float(min_conf)

    label = request.GET.get('label')
    start_id = request.GET.get('start_id')
    start_id = int(float(start_id))
    start_id = start_id if key is None else 0

    return view_image_js(request, data, subset, version, label, start_id, key, min_conf)
