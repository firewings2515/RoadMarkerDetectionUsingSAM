import os
import numpy as np
import cv2

import common

from predictorConfig import PredictorConfig

class SAMMaskSelector:
    def __init__(self, config):
        
        self.config = config
        self.ready = False
        if self.config is None:
            print("use default config")
            self.use_default_config()

    def use_default_config(self):
        config = { 
            'Common':{
                'usage_list': ['default', 'square', 'yellow', 'arrow', 'line'],
                'pixel_cm': 1
            },
            'Predictor': {
                'max_area_threshold': [30000, 1200000, 1200000, 55000, 41000],
                'min_area_threshold': [100, 80000, 60000, 9000, 100],
                'sample_points_interval': [32, 32, 32, 32, 64]
            } 
        }
        self.config = PredictorConfig()
        self.config.set_config_with_dict(config)

    def selector(self, mask, index, usage='default'):
        if usage == 'default':
            return self.default_selector(mask, index, usage)
        elif usage == 'line':
            return self.line_selector(mask, index, usage)
        elif usage == 'arrow': 
            return self.arrow_selector(mask, index, usage)
        elif usage == 'square' or usage == 'yellow':
            return self.square_selector(mask, index, usage)
        return False
    
    def default_selector(self, mask, index, usage='default'):
        self.selected_mask = mask
        pixel_cm = self.config.get_pixel_cm()
        min_area_threshold, max_area_threshold = self.config.get_threshold_from_usage(usage)

        min_area_threshold = min_area_threshold / pixel_cm / pixel_cm
        max_area_threshold = max_area_threshold / pixel_cm / pixel_cm
        area_size = np.sum(mask)
        if ((area_size < min_area_threshold) or (area_size > max_area_threshold)):
            # change from bool to int
            mask_int = mask.astype(np.uint8) * 255
            # check if is long line
            if (common.analyze_line_mask(mask_int, ratio=3, pixel_cm=pixel_cm, index=index)):
                return True
            else:
                print(f"mask{index} area {area_size} larger or smaller than threshold, skip")
                return False
        
        return True

    def square_selector(self, mask, index, usage='square'):
        self.selected_mask = mask
        pixel_cm = self.config.get_pixel_cm()
        min_area_threshold, max_area_threshold = self.config.get_threshold_from_usage(usage)

        min_area_threshold = min_area_threshold / pixel_cm / pixel_cm
        max_area_threshold = max_area_threshold / pixel_cm / pixel_cm

        # area_size = np.sum(mask)
        # if ((area_size < min_area_threshold) or (area_size > max_area_threshold)):
        #     return False
        
        result = np.zeros_like(mask, dtype=np.uint8)
        mask_int = mask.astype(np.uint8) * 255

        selected = False
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask_int, connectivity=8)
        for i in range(1, num_labels):
            x, y, w, h, area = stats[i]
            bounding_area = w * h

            # filter out small components based on bounding box area size
            if bounding_area < min_area_threshold:
                #print(f"mask{index} bounding_area {bounding_area} larger or smaller than threshold, skip")
                continue
            # standard arrow size 500x250  add 20% error range
            
            if bounding_area > max_area_threshold:
                #print(f"mask{index} bounding_area {bounding_area} larger or smaller than threshold, skip")
                continue
            
            # skip line
            ratio = max(w, h) / (min(w,h) + 1e-5)

            if (ratio > 6):
                continue

            result[labels == i] = 1
            selected = True
        self.selected_mask = result
        return selected

    def arrow_selector(self, mask, index, usage='arrow'):
        pixel_cm = self.config.get_pixel_cm()
        min_area_threshold, max_area_threshold = self.config.get_threshold_from_usage(usage)

        min_area_threshold = min_area_threshold / pixel_cm / pixel_cm
        max_area_threshold = max_area_threshold / pixel_cm / pixel_cm

        area_size = np.sum(mask)
        if ((area_size < min_area_threshold) or (area_size > max_area_threshold)):
            # print(f"mask{index} area {area_size} larger or smaller than threshold, skip")
            return False
        
        result = np.zeros_like(mask, dtype=np.uint8)

        mask_int = mask.astype(np.uint8) * 255
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask_int, connectivity=8)

        limit_side_length = common.num_to_pixel_cm(600, pixel_cm)
        real_arrow_bound = common.num_to_pixel_cm(600, pixel_cm) * common.num_to_pixel_cm(300, pixel_cm)

        for i in range(1, num_labels):
            x, y, w, h, area = stats[i]
            bounding_area = w * h
            # filter out small components based on bounding box area size
            if bounding_area < min_area_threshold:
                #print(f"mask{index} bounding_area {bounding_area} larger or smaller than threshold, skip")
                continue
            # standard arrow size 500x250  add 20% error range
            
            if bounding_area > real_arrow_bound:
                #print(f"mask{index} bounding_area {bounding_area} larger or smaller than threshold, skip")
                continue
            
            if (w > limit_side_length or h > limit_side_length):
                #print(f"mask{index} width or height {max(w, h)} larger or smaller than threshold, skip")
                continue
            
            
            result[labels == i] = 1

        self.selected_mask = result

        return True

    def line_selector(self, mask, index, ratio=10, usage='line'):
        pixel_cm = self.config.get_pixel_cm()

        min_area_threshold, max_area_threshold = self.config.get_threshold_from_usage(usage)
        min_area_threshold = min_area_threshold / pixel_cm / pixel_cm
        max_area_threshold = max_area_threshold / pixel_cm / pixel_cm

        area_size = np.sum(mask)
        if (area_size > max_area_threshold or area_size < min_area_threshold):
            return False
        
        mask_int = mask.astype(np.uint8) * 255

        keep_flag, result_mask = common.analyze_all_line_mask(mask_int, ratio=3, pixel_cm=pixel_cm, index=index, max_area_threshold=max_area_threshold, min_area_threshold=min_area_threshold)
        self.selected_mask = result_mask
        if (keep_flag):
            return True
        # if (common.analyze_line_mask(mask_int, ratio=2)):
        #     return True
        else:
            #print(f"mask{index} is not a line, skip")
            return False
    
    def get_selected_mask(self):
        return self.selected_mask
    