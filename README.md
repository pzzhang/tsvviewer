# TSV Viewer
This project is for browser-based TSV file visualization with the following features. 
* Same backend design as in `quickdetection`.
* SVG-based frontend (as in Open Images visualization), showing clearer rendering effect.
* Support two TSV data inputs:
    - Single TSV files with name `train.tsv`, `val.tsv`, `trainval.tsv`, `test.tsv`, as used in `quickdetection`.
    - Three columns (separated by TAB) expected in a TSV file:
        * `image_key`: could be any string. It is not used for visualization, but for easy debug.
        * `annotation`: defined as in below "Supported formats".
        * `base64_encoded_image|image url|image file path`: could be either base64-encoded image, or image url, or image file path.
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
    For simplicity, you may want to just link to my data folder `/data/home/pengchuanzhang/GitHub/tsvviewer/data` to get the first run.

    Another example: for a VOC dataset with `train.tsv` and `test.tsv`, the folder structure is as follows:
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

4. Forward the port to local laptop: Please forward this port 8000 from your aws machine to your laptop via [SSH port forwarding](https://www.ssh.com/academy/ssh/tunneling-example#local-forwarding) (which can also be done using [VS Code](https://code.visualstudio.com/docs/remote/ssh#_forwarding-a-port-creating-ssh-tunnel)). Then you can view the visualization at http://localhost:8000/detection.
