import requests
import io
import base64
import cv2
import numpy as np
import torch
from ultralytics import YOLO
import seam_carving
import inpainting_along_seam as sms
from brisque import BRISQUE
from PIL import Image
        
def display_seam_carving(img, new_width, new_height, mask, prot_people):
    target_arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    target_height, target_width, _ = target_arr.shape
    seam_mask = None
    if mask is not None:
        seam_mask = np.array(Image.open(mask).convert("L"))
    if prot_people:
       seam_mask = get_people_mask(img, target_width, target_height)
    carved_img = seam_carving.resize(
        target_arr,
        size=(new_width, new_height),
        energy_mode="forward",
        order="width-first",
        keep_mask=seam_mask,
    )
    carved_img = cv2.cvtColor(np.array(carved_img), cv2.COLOR_RGB2BGR)
    transformed_carved = Image.fromarray(carved_img)
    return transformed_carved

#This method is currently only supported with simple Seam-carving
def get_people_mask(target, size_witdh, size_height):
        people_masks = []
        model = YOLO('yolov8l-seg.pt')
        results = model(target, imgsz = size_witdh)
        count = 0
        for result in results:
            for box in result.boxes.cpu().numpy():
                cls = int(box.cls[0])
                if cls == 0 and box.conf[0] > 0.5:
                    m = torch.squeeze(result.masks[count].data)
                    composite = torch.stack((m, m, m), 2)
                    composite_img = composite.cpu().numpy().astype(np.uint8)
                    tempX, tempY, _ = composite_img.shape
                    white_image = np.ones((tempX, tempY, 3), np.uint8) * 255
                    tmp = white_image * composite_img
                    people_masks.append(tmp)
                count += 1
        if len(people_masks) > 0:
            mask_img = people_masks[0]
            msk_count = 0
            for mask in people_masks:
                mask_img = (mask_img + people_masks[msk_count]) / 2
                msk_count += 1
            mask_img = cv2.resize(mask_img, (size_witdh, size_height))
            cv2.imshow("result", mask_img)
            mask_img = np.clip(mask_img, 0, 255).astype(np.uint8)
            return Image.fromarray(mask_img).convert("L")
        
def get_clip_prompt(img):
    url = "http://127.0.0.1:7860"

    payload = {
        "image": img,
        "model": "clip",
    }
    response = requests.post(url=f'{url}/sdapi/v1/interrogate', json=payload)
    r = response.json()
    info = r["caption"]
    print(info)
    return info

def outpaint_image(src, prompt, seed, width, height, amount):
    url = "http://127.0.0.1:7860"
    payload = {
        "prompt": prompt,
        "seed": seed,
        "batch_size": amount,
        "steps": 20,
        "cfg_scale": 7,
        "width": width,
        "height": height,
        "alwayson_scripts": {
            "controlnet": {
                "args": [
                    {
                        "input_image": src,
                        "module": "inpaint_only+lama",
                        "model": "control_v11p_sd15_inpaint [ebff9138]",
                        "resize_mode": 2,
                        "control_mode": 2,
                        "pixel_perfect": True
                    }
                ]
            }
        }
    }

    response = requests.post(url=f'{url}/sdapi/v1/txt2img', json=payload)

    results = []
    r = response.json()
    for i in r['images']:
        image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0])))
        results.append(image)
    return results

#This code is not used anywhere as it merely produces the Inpainting mask and and extended input image with additional image space.
#These two outputs have been used manually in Automatic1111 to test this alternative approach
def get_seam_inpaint_mask(input, expand_height):
    target_arr = cv2.cvtColor(np.array(input), cv2.COLOR_RGB2BGR)
    results = sms.get_single_seam_mask(target_arr, expand_height)
    
    image_to_inpaint = results[0]
    result_mask = results[1]
    
    return image_to_inpaint, result_mask


#This is the main method for the image orientation switch
def automatic_reorientation(input, prompt, seam_size, outpaint_size, seed, use_auto_prompt):
    output_path = "./output.png" #Replace with desired path
    inputWidth, inputHeight = input.size[:2]
    target_aspect_ratio = inputHeight/inputWidth
    
    outpainting_step = outpaint_size
    seam_step = seam_size
    
    #Determine whether to switch to landscape or to portrait
    larger_side = max(inputWidth, inputHeight)
    
    if inputWidth == larger_side:
        newWidth = inputWidth
        newHeight = inputHeight + outpainting_step
        toPortrait = True
    else:
        newWidth = inputWidth + outpainting_step
        newHeight = inputHeight
        toPortrait = False
    
    currentWidth = inputWidth
    currentHeight = inputHeight
    currentImage = input
    
    target_arr = cv2.cvtColor(np.array(input), cv2.COLOR_RGB2BGR)
    _, bytes = cv2.imencode('.png', target_arr)
    encoded_image = base64.b64encode(bytes).decode('utf-8')
    
    prompt_to_use = prompt
    if use_auto_prompt:
        prompt_to_use = get_clip_prompt(encoded_image)
    
    #Repeat the process until the opposite aspect ratio is achieved
    while (abs(currentWidth/currentHeight - target_aspect_ratio) > 0.01):
        print(abs(currentWidth/currentHeight - target_aspect_ratio))
        result = outpaint_image(encoded_image, prompt_to_use, seed, newWidth, newHeight, 1)[0]
        
        if toPortrait:
            after_carve = display_seam_carving(result, result.width - seam_step, result.height + seam_step, None, False)
        else:
            after_carve = display_seam_carving(result, result.width + seam_step, result.height - seam_step, None, False)
        currentImage = after_carve
        currentWidth = after_carve.width
        currentHeight = after_carve.height 

        #Check if another Outpainting step is necessary, otherwise do the rest of the process with Seam-carving
        if toPortrait:
            required_rest_pixels = currentWidth - (currentHeight * target_aspect_ratio)
            if (required_rest_pixels > outpainting_step):
                newWidth = currentWidth
                newHeight = currentHeight + outpainting_step
            else:
                final_carve = display_seam_carving(result, currentWidth - required_rest_pixels, currentHeight, None, False)
                currentWidth, currentHeight = final_carve.width, final_carve.height
                currentImage = final_carve
                currentImage.save(output_path) 
        else:
            required_rest_pixels = currentHeight - (currentWidth / target_aspect_ratio)
            if (required_rest_pixels > outpainting_step):
                newWidth = currentWidth + outpainting_step
                newHeight = currentHeight
            else:
                final_carve = display_seam_carving(result, currentWidth, currentHeight - required_rest_pixels, None, False)
                currentWidth, currentHeight = final_carve.width, final_carve.height
                currentImage = final_carve
                currentImage.save(output_path)
    obj = BRISQUE(url=False)
    print("BRISQUE score: " + str(obj.score(currentImage)))
    return currentImage
