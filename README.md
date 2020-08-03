# TSV Viewer
This project is for browser-based TSV file visualization with the following features. 
* Same backend design as in `quickdetection`.
* SVG-based frontend (as in Open Images visualization), showing clearer rendering effect.
* Support two TSV data inputs:
    - Single TSV files with name `train.tsv`, `val.tsv`, `trainval.tsv`, `test.tsv`, as used in `quickdetection`.
    - Yaml based defination, as used in `maskrcnn-benchmark`. Expected entries include:  
        * `img`: image tsv file, with base64-encoded image in the last column.
        * `label`: label tsv file, with label in the last column
        * `prediction`: (optional) prediction tsv file, with the same format as label tsv.
        * `labelmap`: (optional) labelmap file. If not provided, labelmap will be created from the label tsv file.
* Supported formats
    - json format as in `quickdetection`:      
    `[{"class":"dog", "rect": [10,10,100,100]},{...}]`
    - tagging label format as in `imagetagging2`:  
    `tag1;tag2;tag3;...`, or  
    `tag1,tag2,tag3,...`
    - relation json format for Visual Genome:  
    `{"objects": [{"class":"dog", "rect": [10,10,100,100], "attributes": ["black", "puppy"]}, {...}], ...}`
    - caption json format:  
    `[{"caption": "A seagull flying close to the ocean."}, {"caption": "..."}]`

## Requirements
* `Python 3.6` is tested.

## Installation

1. First, clone this repo, install python packages, and create a `data` folder.
    ```
    git clone URL_TO_THIS_REPO
    cd tsvviewer
    ./setup.sh
    mkdir data
    ```

2. Second, copy (or link) a dataset into a sub-folder under `data`.

    For example, for a VOC dataset with `train.tsv` and `test.tsv`, the folder structure is as follows:
    ```
    .../tsvviewer/data$ tree voc20
    voc20
    ├── test.tsv
    └── train.tsv
    ```

    [Optional] if you want to build index and check the format issue, you can run the following command:
    ```
    python utils/tsv_dataset.py path_to_dataset
    ```
    Otherwise, the index will be built when the dataset is visited first time from browser.

3. Start the viewer,

    ```
    python manage.py runserver 0:8000
    ```
    and open http://localhost:8000/detection to check the visualization.
