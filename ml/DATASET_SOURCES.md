# Dataset sources and selection

Research and access date: 2026-10-02.

## Selected source

**Custom Bangladeshi E-Waste Image Dataset for Object Detection and Recognition**, Tanzila Afrin and Azizul Abedin Azmi, Mendeley Data V1, DOI [10.17632/77383kmdnw.1](https://doi.org/10.17632/77383kmdnw.1), [dataset record](https://data.mendeley.com/datasets/77383kmdnw/1).

- Record states 2,157 images in 12 classes: Battery Waste, Glass Waste, Keyboard, Light Bulb, Medical Waste, Metal Waste, Mobile, Mouse, Organic Waste, Paper Waste, PCB and Plastic Waste.
- Record describes handheld/smartphone photography under varied lighting and backgrounds.
- License recorded by Mendeley: **CC BY 4.0**. The downloaded archive's embedded Roboflow README also names CC BY 4.0 and the underlying export [azizul-abedin-azmi-uwbiw/e-waste-uvzkj, version 5](https://universe.roboflow.com/azizul-abedin-azmi-uwbiw/e-waste-uvzkj/dataset/5).
- CC BY 4.0 permits sharing and adaptation, including commercial use, subject to attribution, license link and indication of changes. The archive identifies a dataset-level uploader declaration but does not include per-image creator/source records; that provenance limitation remains.
- The archive actually contains 2,157 JPEGs plus YOLO labels, split into `train`, `valid` and `test`. Its README says training augmentation created three variants from some source images. The clean pipeline checks this claim against filenames, retains all variants only in the existing training partition, groups variants by source stem, and verifies no source stem crosses splits. Validation and test images are not augmented by this pipeline.
- Image-level labels are derived only for images with one unique annotated class. The current archive audit found no multi-class frames. The selected image-classification taxonomy is battery waste, keyboard, light bulb, mobile phone, mouse and printed circuit board. Glass, medical, metal, organic, paper and plastic waste are excluded from training and reserved for out-of-domain analysis.
- Limitations: no item-level identity, acquisition protocol, or per-image license manifest; many classes have few distinct source images; labels identify object type, not condition or whether an item is legally e-waste. The split is source-filename grouped, but source filenames cannot prove distinct physical objects.

## Other candidates considered

| Candidate | Source / stated license | Fit and reason not selected |
|---|---|---|
| E-Waste Dataset by Iliev et al. | [Roboflow Universe dataset](https://universe.roboflow.com/ewaste-classification-ljp7s/e-waste-dataset-r0ojc-vzyti), CC BY 4.0; page describes 19,613 annotated images and 77 device classes. | E-waste relevant and larger, but detection labels, mixed box/polygon annotations and a long list of contributed upstream datasets make this first classification baseline harder to curate and audit for image-level task fit and per-image provenance. |
| GIZ e-waste scrapyard images with YOLO labels | [Hugging Face dataset card](https://huggingface.co/datasets/GIZ/e-waste-dataset-yolo-labels), CC BY 4.0; GIZ says photos came from scrapyards in Ghana in October 2025. | Strong real-world domain fit and clear organization, but 2.83 GB and object annotations; its public dataset viewer reports a generation error. It is a good later external-domain evaluation source after individual annotations and split groupings are audited. |
| Laptop component photographic dataset | [Mendeley / article](https://pmc.ncbi.nlm.nih.gov/articles/PMC11629584/), 3,640 original photos, 26 laptop-component classes, two phone cameras. | Strong real capture conditions, but predicts laptop internals (for example RAM, hinges and screws), which do not match the current whole-item categories. We did not select it because the current app taxonomy is broader and the dataset is much larger after augmentation. |

## Attribution

Afrin, T.; Azmi, A. A. (2025). *Custom Bangladeshi E-Waste Image Dataset for Object Detection and Recognition*, Mendeley Data, V1. https://doi.org/10.17632/77383kmdnw.1. Dataset licensed under CC BY 4.0 as stated on the record and in the archive. Changes for this work: selected six e-waste classes, converted single-class YOLO frames to folder labels, removed corrupt/invalid images if any, checked duplicate/group leakage, and trained MobileNetV2.
