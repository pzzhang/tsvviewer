let colors = {};
let type_to_linetype = { 'gt': [], 'pred': [5] };

function generate_palette(total_colors) {
    var color_palette = "#FFFF00 #FF0000 #0000FF #00FF00 #FF00FF #00FFFF".split(" ");
    var bit_mask = [255, 128, 64, 32, 16, 8, 4, 2, 1]
    for (var signature = color_palette.length + 1; color_palette.length < total_colors; signature++) {
        var c = [0, 0, 0];
        var sucess = true;
        for (var sig = 1, b = 0; sig <= signature; sig<<=1, b++) {
            if ((signature & sig) > 0)
                if (c[b % 3] + bit_mask[Math.floor(b / 3)] <= 255)
                    c[b % 3] += bit_mask[Math.floor(b / 3)];
                else {
                    sucess = false;
                    break
                }
        }
        if (sucess)
        {
            c = ("#" + c[0].toString(16).padStart(2, "0") + c[1].toString(16).padStart(2, "0") + c[2].toString(16).padStart(2, "0")).toUpperCase();
            if (color_palette.indexOf(c) <= 0)
                color_palette.push(c);
        }
    }
    return color_palette;
}

function prepare_label_colors(labelmap) {
    palette = generate_palette(labelmap.length).reverse();
    for (var label of labelmap)
        colors[label] = palette.pop()
}

function create_svg_rect(rect, color, t) {
    var r = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    r.setAttribute("vector-effect", "non-scaling-stroke");
    r.setAttribute("stroke-alignment", "inner");
    r.setAttribute("x", String(rect[0]));
    r.setAttribute("y", String(rect[1]));
    r.setAttribute("width", String(rect[2] - rect[0]));
    r.setAttribute("height", String(rect[3] - rect[1]));
    r.setAttribute("fill", "none");
    if (t === 'pred')
        r.setAttribute("stroke-dasharray", "10 5");
    r.setAttribute("stroke-width", "1.5pt");
    r.setAttribute("stroke", color);
    return r
}

function create_svg_circle(cx, cy, radius, color, t) {
    var r = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    r.setAttribute("vector-effect", "non-scaling-stroke");
    r.setAttribute("stroke-alignment", "inner");
    r.setAttribute("cx", cx);
    r.setAttribute("cy", cy);
    r.setAttribute("r", radius);
    r.setAttribute("fill", color);
    r.setAttribute("stroke", color);
    r.setAttribute("stroke-width", "2");
    return r
}

function create_svg_line(x1, y1, x2, y2, color, t) {
    var r = document.createElementNS("http://www.w3.org/2000/svg", "line");
    r.setAttribute("vector-effect", "non-scaling-stroke");
    r.setAttribute("x1", x1);
    r.setAttribute("y1", y1);
    r.setAttribute("x2", x2);
    r.setAttribute("y2", y2);
    if (t === 'pred')
        r.setAttribute("stroke-dasharray", "10 5");
    r.setAttribute("stroke-width", "2");
    r.setAttribute("stroke", color);
    return r
}

function create_svg_text(text, x, y, font_size, color) {
    let t = document.createElementNS("http://www.w3.org/2000/svg", "text");
    t.textContent = text
    t.setAttribute("font-size", font_size);
    t.setAttribute("dominant-baseline", "hanging");
    t.setAttribute("font-family", "arial");
    t.setAttribute("x", String(x));
    t.setAttribute("y", String(y));
    t.setAttribute("fill", color);
    return t
}

function add_svg_objects(svg, t, rects) {
    for (let r = 0; r < rects.length; r++) {
        if (!("rect" in rects[r]))
            continue;
        let rect = rects[r]["rect"];
        let label = rects[r]["class"];
        let attr = ""
        if ("attributes" in rects[r])
            attr = rects[r]["attributes"].join(", ")

        let color = colors[label];

        let svg_r = create_svg_rect(rect, color, t);
        svg_r.setAttribute("id", svg.getAttribute("id").replace("svg", "") + "_" + t + "_box" + String(r));
        svg_r.setAttribute("class", label);
        svg_r.setAttribute("type", t);
        svg.appendChild(svg_r);

        let font_size = svg.viewBox.baseVal.width / svg.clientWidth * 13
        label_text = label
        if ("conf" in rects[r])
            label_text += ":" + rects[r]["conf"].toFixed(3)
        let svg_t = create_svg_text(label_text, rect[0] + 1, rect[1] + 1, font_size, color);
        svg_t.setAttribute("id", svg.getAttribute("id").replace("svg", "") + "_" + t + "_text" + String(r));
        svg.appendChild(svg_t);
        svg_t = create_svg_text(attr, rect[0] + 1, rect[1] + 1 + font_size, font_size, color);
        svg_t.setAttribute("id", svg.getAttribute("id").replace("svg", "") + "_" + t + "_att" + String(r));
        svg.appendChild(svg_t);
    }
}

function add_svg_object_relations(svg, t, annotations) {
    rects = annotations["objects"]          // list of object rects
    relations = annotations["relations"]    // list of relations, each as a dict
    for (let r = 0; r < relations.length; r++) {
        let name = relations[r]["class"]
        let s = relations[r]["subj_id"]
        let o = relations[r]["obj_id"]
        rc = rects[s]["rect"]
        s_cx = (rc[0] + rc[2]) / 2
        s_cy = (rc[1] + rc[3]) / 2
        rc = rects[o]["rect"]
        o_cx = (rc[0] + rc[2]) / 2
        o_cy = (rc[1] + rc[3]) / 2
        relation_name = relations[r]["class"]

        color = "#00FF00"   // relation line color: green
        let svg_rel = create_svg_line(s_cx, s_cy, o_cx, o_cy, color, t);
        svg_rel.setAttribute("id", svg.getAttribute("id").replace("svg", "") + "_" + t + "_rel" + String(r));
        svg_rel.setAttribute("class", relation_name);
        svg_rel.setAttribute("type", t);
        svg.appendChild(svg_rel);

        color = "#FF0000"   // subject color:red
        radius = svg.viewBox.baseVal.width / svg.clientWidth * 1.5
        let svg_sub = create_svg_circle(s_cx, s_cy, radius, color, t);
        svg_sub.setAttribute("id", svg.getAttribute("id").replace("svg", "") + "_" + t + "_sub" + String(r));
        svg_sub.setAttribute("class", relation_name);
        svg_sub.setAttribute("type", t);
        svg.appendChild(svg_sub);

        color = "#800080"   // object color: purple
        let svg_obj = create_svg_circle(o_cx, o_cy, radius, color, t);
        svg_obj.setAttribute("id", svg.getAttribute("id").replace("svg", "") + "_" + t + "_obj" + String(r));
        svg_obj.setAttribute("class", relation_name);
        svg_obj.setAttribute("type", t);
        svg.appendChild(svg_obj);

        t_cx = (s_cx + o_cx) / 2
        t_cy = (s_cy + o_cy) / 2
        color = "#00FF00"   // relation name color: green
        let font_size = svg.viewBox.baseVal.width / svg.clientWidth * 13
        label_text = relation_name
        let svg_t = create_svg_text(label_text, t_cx, t_cy, font_size, color);
        svg_t.setAttribute("id", svg.getAttribute("id").replace("svg", "") + "_" + t + "_relname" + String(r));
        svg.appendChild(svg_t);
    }

}

function add_svg_elements(svg, type_to_annotations) {
    for (let t in type_to_annotations) {
        add_svg_objects(svg, t, type_to_annotations[t]["objects"])
        if ("relations" in type_to_annotations[t])
            add_svg_object_relations(svg, t, type_to_annotations[t])
    }
}

function add_svg_image_divs(all_url, all_key, all_type_to_annotations) {
    let image_cols = document.getElementById("grid").childElementCount;
    let j = 1;
    for (i = 0; i < all_url.length; i++) {
        let elem = document.createElementNS("http://www.w3.org/2000/svg", "svg");                
        elem.id = 'svg' + i.toString();
        elem.setAttributeNS("http://www.w3.org/2000/xmlns/", "xmlns:xlink", "http://www.w3.org/1999/xlink");
        elem.setAttribute("style", "border:1px solid #d3d3d3; width:100%; margin-bottom:1em");
        elem.setAttribute("viewBox", "0 0 1 1");
        elem.onclick = function(img_id) {
            return function() {
                openViewer(img_id);
            }
        } (i);

        let img = document.createElement("img");
        img.onload = function(svg, preload_im, type_to_annotations) {
            return function() {
                let svg_img = document.createElementNS("http://www.w3.org/2000/svg", "image");
                svg_img.id = svg.getAttribute("id").replace("svg", "img");
                svg_img.setAttributeNS("http://www.w3.org/1999/xlink", "href", preload_im.src);
                svg.setAttribute("viewBox", "0 0 " + preload_im.naturalWidth + " " + preload_im.naturalHeight);
                svg.appendChild(svg_img);
                add_svg_elements(svg, type_to_annotations);
                update_svg_objects(svg, 
                    document.getElementById('show_label').checked,
                    document.getElementById('show_all').checked,
                    document.getElementById('show_gt').checked,
                    document.getElementById('show_pred').checked,
                    getUrlParameter(window.location.href, "label", ""));
            }
        }(elem, img, all_type_to_annotations[i]);
        img.src = all_url[i]

        let id = "col" + j.toString();

        if (all_key.length > i) {
            let key = all_key[i];
            let p = document.createElement('p');
            p.setAttribute("id", "id"+String(i))
            p.setAttribute("style", "width:"+(window.innerWidth / image_cols-50)+"px");
            key = "Id: " + key;
            p.appendChild(document.createTextNode(key))
            p.setAttribute("class", "text-block");
            document.getElementById(id).appendChild(p);
        }

        if (all_type_to_annotations.length > i) {
            let type_to_annotations = all_type_to_annotations[i];
            for (let t in type_to_annotations) {
                let img_info = ""
                let rects = type_to_annotations[t]["objects"];
                let all_class = {}
                for (let j = 0; j < rects.length; j++) {
                    if ('class' in rects[j] && !rects[j]['class'].startsWith('-'))
                        all_class[rects[j]['class']] = 'x'
                }
                list_of_keys = Object.keys(all_class)
                if (list_of_keys.length > 0) {
                    keys = list_of_keys.join(', ');
                    img_info = t.replace("gt", "Gt").replace('pred', "Pred") + ": " + keys;
                }
                for (let j = 0; j < rects.length; j++) {
                    if ('caption' in rects[j]) {
                        if (img_info.length > 0)
                            img_info += "<br>";
                        img_info += "Caption" + j + ": " + rects[j]['caption']
                    }
                }

                let p = document.createElement('p');
                p.setAttribute("id", "gt"+String(i))
                p.setAttribute("style", "width:"+(window.innerWidth / image_cols-50)+"px");
                p.innerHTML = img_info;
                document.getElementById(id).appendChild(p);
            }
        }

        document.getElementById(id).appendChild(elem);
        j = j < image_cols ? j + 1 : 1;
    }
}

function update_svg_objects(svg, showlabel, showall, show_gt, show_pred, cls) {
    let rects = svg.getElementsByTagNameNS("http://www.w3.org/2000/svg", "rect");
    for (let rect of rects) {
        t = rect.getAttribute('type')
        type_visible = (t === 'gt' && show_gt) || (t === 'pred' && show_pred);

        let box_visible = showall || rect.getAttribute("class").toLowerCase() === cls.toLowerCase() || cls === "";
        rect.setAttribute("visibility", box_visible && type_visible ? "visible" : "hidden");

        t_label = svg.getElementById(rect.getAttribute("id").replace("_box", "_text"))
        t_att = svg.getElementById(rect.getAttribute("id").replace("_box", "_att"))
        t_label.setAttribute("visibility", box_visible && type_visible && showlabel ? "visible" : "hidden");
        t_att.setAttribute("visibility", box_visible && type_visible && showlabel ? "visible" : "hidden");
    }
}

function update_images(all_type_to_annotations, showlabel, showall, show_textinfo, show_gt, show_pred, cls) {
    for (i = 0; i < all_type_to_annotations.length; i++) {
        let svg = document.getElementById('svg' + i);
        update_svg_objects(svg, showlabel, showall, show_gt, show_pred, cls);

        let id_text = document.getElementById('id' + i);
        id_text.style.display = show_textinfo ? "block" : "none";
        let gt_text = document.getElementById('gt' + i);
        gt_text.style.display = show_textinfo ? "block" : "none";
    }
    let svg = document.getElementById('viewer_svg');
    update_svg_objects(svg, showlabel, showall, show_gt, show_pred, cls);
}

function storageAvailable(type) {
    var storage;
    try {
        storage = window[type];
        var x = '__storage_test__';
        storage.setItem(x, x);
        storage.removeItem(x);
        return true;
    }
    catch(e) {
        return e instanceof DOMException && (
            // everything except Firefox
            e.code === 22 ||
            // Firefox
            e.code === 1014 ||
            // test name field too, because code might not be present
            // everything except Firefox
            e.name === 'QuotaExceededError' ||
            // Firefox
            e.name === 'NS_ERROR_DOM_QUOTA_REACHED') &&
            // acknowledge QuotaExceededError only if there's something already stored
            (storage && storage.length !== 0);
    }
}

function onClickShowall() {
    localStorage.setItem('show_all', JSON.stringify(document.getElementById('show_all').checked));
    onClick_abstraction()
}

function onClickShowlabel() {
    localStorage.setItem('show_label', JSON.stringify(document.getElementById('show_label').checked));
    onClick_abstraction()
}

function onClickShowtextinfo() {
    localStorage.setItem('show_textinfo', JSON.stringify(document.getElementById('show_textinfo').checked));
    onClick_abstraction()
}

function onClickShowGt() {
    localStorage.setItem('show_gt', JSON.stringify(document.getElementById('show_gt').checked));
    onClick_abstraction()
}

function onClickShowPred() {
    localStorage.setItem('show_pred', JSON.stringify(document.getElementById('show_pred').checked));
    onClick_abstraction()
}

function onClick_abstraction() {
    update_images(all_type_to_annotations,
        document.getElementById('show_label').checked,
        document.getElementById('show_all').checked,
        document.getElementById('show_textinfo').checked,
        document.getElementById('show_gt').checked,
        document.getElementById('show_pred').checked,
        getUrlParameter(window.location.href, "label", ""));
}

var resizeCallback = function(new_num_cols) {
    var grid = document.getElementById("grid");
    var numberOfColumns = grid.childElementCount;

    if (typeof new_num_cols === "undefined") {
        var w = grid.getBoundingClientRect().width;
        new_num_cols = w > 1000 ? 5 : w > 750 ? 4 : w > 500 ? 3 : w > 250 ? 2 : 1;
    }

    if (new_num_cols !== numberOfColumns) {
        createColumns(new_num_cols);
        add_svg_image_divs(all_url, all_key, all_type_to_annotations);
        onClick_abstraction();
    }
}

function createColumns(numberOfColumns) {
    var grid = document.getElementById("grid");
    grid.innerHTML = "";
    for (var i = 1; i < numberOfColumns + 1; ++i) {
        var div = document.createElement("div");
        div.id = "col" + String(i);
        div.className = "column";
        div.style.width = String(100 / numberOfColumns) + "%";
        grid.appendChild(div);
    }      
}

function setViewerSize(preload_im)
{
    var viewer = document.getElementById("viewer");
    var navbar = document.getElementById("navbar");
    var viewer_wrap = document.getElementById("viewer_wrap");
    viewer_wrap.style.position = "relative";

    var bs = 3;    // border_size, see CSS definition
    var xx = 10;
    var yy = navbar.getBoundingClientRect().bottom + 10;
    var ww = viewer.getBoundingClientRect().width - 20;
    var hh = viewer.getBoundingClientRect().height - yy - 10;

    if (preload_im.naturalWidth / preload_im.naturalHeight > ww / hh) {
        // horizontal image, set width and adjust height
        height = ww * preload_im.naturalHeight / preload_im.naturalWidth;
        viewer_wrap.style.left = xx - bs + "px";
        viewer_wrap.style.top = yy - bs + (hh - height) / 2 + "px";
        viewer_wrap.style.width = ww + 2*bs + "px";
        viewer_wrap.style.height = height + 2*bs + "px";
    }
    else {
        // vertical image, set height and adjust width
        width = hh * preload_im.naturalWidth / preload_im.naturalHeight;
        viewer_wrap.style.left = xx - bs + (ww - width) / 2 + "px";
        viewer_wrap.style.top = yy - bs + "px";
        viewer_wrap.style.width = width + 2*bs + "px";
        viewer_wrap.style.height = hh + 2*bs + "px";
    }
}

function openViewer(img_id)
{
    img_url = all_url[img_id];
    type_to_annotations = all_type_to_annotations[img_id];
    let img = document.createElement("img");
    img.onload = function(preload_im) {
        return function() {
            setViewerSize(preload_im);

            var svg_img = document.getElementById("viewer_img");
            svg_img.setAttributeNS("http://www.w3.org/1999/xlink", "href", preload_im.src);
            var svg = document.getElementById("viewer_svg");
            svg.setAttribute("viewBox", "0 0 " + preload_im.naturalWidth + " " + preload_im.naturalHeight);
            add_svg_elements(svg, type_to_annotations);
            update_svg_objects(svg, 
                document.getElementById('show_label').checked,
                document.getElementById('show_all').checked,
                document.getElementById('show_gt').checked,
                document.getElementById('show_pred').checked,
                getUrlParameter(window.location.href, "label", ""));

            viewer = document.getElementById("viewer");
            viewer.imageid = img_id;
            // force cursor change while mouse is not moving 
            viewer.style.cursor = "zoom-out";
            viewer.style.visibility = "visible";
        }

    } (img);
    img.src = img_url;
}

function clearViewer()
{
    var view_svg = document.getElementById("viewer_svg");
    view_svg.parentNode.replaceChild(view_svg.cloneNode(false), view_svg);

    viewer_img = document.createElementNS("http://www.w3.org/2000/svg", "image");
    viewer_img.id = "viewer_img";
    document.getElementById("viewer_svg").appendChild(viewer_img)
}

function closeViewer()
{
    clearViewer();

    viewer = document.getElementById("viewer");
    // force cursor change while mouse is not moving 
    viewer.style.cursor = "";
    viewer.style.visibility = "hidden";
}

function keydownCallback(evt)
{
    evt = evt || window.event;
    if (document.getElementById("viewer").style.visibility === "visible") {
        if (evt.key === "ArrowRight") {
            img_id = document.getElementById("viewer").imageid;
            if (img_id < all_url.length - 1) {
                clearViewer();
                openViewer(img_id + 1);
            }
        }
        else if (evt.key === "ArrowLeft") {
            img_id = document.getElementById("viewer").imageid;
            if (img_id > 0) {
                clearViewer();
                openViewer(img_id - 1);
            }
        }
        else if (evt.key === "Escape")
            closeViewer();
    }

    if (evt.key === "-") {
        let numberOfColumns = document.getElementById("grid").childElementCount;
        if (numberOfColumns < 15)
            resizeCallback(numberOfColumns + 1);
    } else if (evt.key === "+") {
        let numberOfColumns = document.getElementById("grid").childElementCount;
        if (numberOfColumns > 1)
            resizeCallback(numberOfColumns - 1);
    }

}

function getUrlParameter(url, parameter, defaultvalue){
    urlParams = new URLSearchParams(url.split('?')[1]);
    value = urlParams.get(parameter)
    return value === null ? defaultvalue : decodeURIComponent(value);
}

function setUrlParameter(url, key, value) {
    var key = encodeURIComponent(key),
        value = encodeURIComponent(value);

    var baseUrl = url.split('?')[0],
        newParam = key + '=' + value,
        params = '?' + newParam;

    if (url.split('?')[1] === undefined){ // if there are no query strings, make urlQueryString empty
        urlQueryString = '';
    } else {
        urlQueryString = '?' + url.split('?')[1];
    }

    // If the "search" string exists, then build params from it
    if (urlQueryString) {
        var updateRegex = new RegExp('([\?&])' + key + '=[^&]*');
        var removeRegex = new RegExp('([\?&])' + key + '=[^&;]+[&;]?');

        if (value === undefined || value === null || value === '') { // Remove param if value is empty
            params = urlQueryString.replace(removeRegex, "$1");
            params = params.replace(/[&;]$/, "");
    
        } else if (urlQueryString.match(updateRegex) !== null) { // If param exists already, update it
            params = urlQueryString.replace(updateRegex, "$1" + newParam);
    
        } else if (urlQueryString == '') { // If there are no query strings
            params = '?' + newParam;
        } else { // Otherwise, add it to end of query string
            params = urlQueryString + '&' + newParam;
        }
    }

    // no parameter was set so we don't need the question mark
    params = params === '?' ? '' : params;

    return baseUrl + params;
}

function removeUrlParameter(url, key) {
    var urlParts = url.split('?');
    var params = new URLSearchParams(urlParts[1]);
    params.delete(key);
    var newUrl = urlParts[0] + '?' + params.toString()
    return newUrl;
}

function setup_menu() {
    data = getUrlParameter(window.location.href, "data", "");
    version = getUrlParameter(window.location.href, "version", "0");
    subset = getUrlParameter(window.location.href, "subset", "");
    if (version !== "0")
        subset += "-v" + version;
    $("#subset_name")[0].innerHTML = subset;
    document.title = subset + " - [" + data + "] - TSV Viewer"

    for (let opt of ["show_label", "show_all", "show_textinfo", "show_gt", "show_pred"])
        document.getElementById(opt).checked = localStorage.getItem(opt)
            ? JSON.parse(localStorage.getItem(opt))
            : true;
}

function changeClass(cls) {
    if (cls === "any")
        url = removeUrlParameter(window.location.href, "label");
    else
        url = setUrlParameter(window.location.href, "label", cls);
    closeViewer();
    window.history.pushState("", document.title, url);
    location.reload();
}

function setup_typeahead_class_search() {
    var substringMatcher = function (strs) {
        return function findMatches(q, cb) {
            var matches, substringRegex;

            // an array that will be populated with substring matches
            matches = [];

            // regex used to determine if a string contains the substring `q`
            substrRegex = new RegExp(q, 'i');

            // iterate through the pool of strings and for any string that
            // contains the substring `q`, add it to the `matches` array
            $.each(strs, function (i, entry) {
                if (substrRegex.test(entry[0])) {
                    matches.push(entry);
                }
            });

            cb(matches);
        };
    };
    $("#class_search").typeahead({
        hint: true,
        highlight: true,
        minLength: 0
    }, {
        display: function(entry) {
            return entry[0] + ' [' + entry[1] + ']';
        },
        source: substringMatcher(label_count),
        limit: 1E4
    });
    $("#class_search").on("typeahead:selected", function(event, entry) {
        changeClass(entry[0]);
    });
    $("#class_search").on("click", function() {
        $(this).typeahead("val", "")
    });
    cls = getUrlParameter(window.location.href, "label", "any");
    $("#class_search").typeahead("val", cls);
}

function onClickRandomClass() {
    randIdx = Math.floor(Math.random() * (label_count.length - 1)) + 1;
    if (randIdx < label_count.length) {
        cls = label_count[randIdx][0]
        changeClass(cls);
    }
}

function startup()
{
    if (!storageAvailable('localStorage')) {
        console.log("Too bad, no localStorage for us")
    }
    
    window.addEventListener("popstate", function(e) {
        document.location.reload();      
    });

    labelmap = new Array(label_count.length - 1)
    for (let i = 1; i < label_count.length; i++)
        labelmap[i] = label_count[i][0];
    prepare_label_colors(labelmap);
    setup_menu();
    setup_typeahead_class_search();
    resizeCallback();
}