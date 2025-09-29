import os
import cv2
import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS
import ssdeep
import hashlib


class SimpleDetective:
    '''
    The SimpleDetective class implements an expert system to identify modified images
    by comparing them against a set of original target images using three rules:
    1. Metadata Analysis
    2. Fuzzy Hashing
    3. Template Matching    
    '''
    
    def __init__(self):
        self.targets = {}
        '''Initialize and loads target images'''
        
    
    def register_targets(self, folder):
        '''
        Loads all the images from the given folder and computes their ratios and values.
        Args are the folder path and returns the # of successfully registered images.
        '''

        ''' Validates folder path '''
        if not os.path.exists(folder):
            raise FileNotFoundError(f"Folder {folder} does not exist")
        
        print(f"Registering targets from {folder}...")
        
        ''' verifies the images from the folder in various formats and computes their signatures. '''
        for filename in os.listdir(folder):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                filepath = os.path.join(folder, filename)
                try:
                    signature = self._compute_signature(filepath)
                    self.targets[filename] = signature
                except Exception as e:
                    print(f"Warning: Failed to register {filename}: {e}")
        
        print(f"Successfully registered {len(self.targets)} target images")
    
    def _compute_signature(self, image_path):
        '''
        computes the signature of an image including metadata, fuzzy hash, and templates. 
        Args: image_path - path to the image file. returns a dictionary with the signature.
        '''
        signature = {}
        

        signature['path'] = image_path
        signature['filename'] = os.path.basename(image_path)
        
        # File metadata
        stat_info = os.stat(image_path)
        signature['file_size'] = stat_info.st_size
        signature['modification_time'] = stat_info.st_mtime
        
        # Load image for analysis
        try:
            # metadata using PIL
            pil_image = Image.open(image_path)
            signature['dimensions'] = pil_image.size
            signature['mode'] = pil_image.mode
            signature['format'] = pil_image.format
            
            #reads the EXIF data(model type/which lens type) if available
            exif_data = {}
            if hasattr(pil_image, '_getexif') and pil_image._getexif() is not None:
                exif = pil_image._getexif()
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    exif_data[tag] = value
            signature['exif'] = exif_data
            
            # Convert to numpy array for OpenCV operations and saves the shape of the image
            cv_image = cv2.imread(image_path)
            if cv_image is not None:
                signature['cv_shape'] = cv_image.shape
                
                # Compute image statistics for metadata rule
                signature['mean_intensity'] = np.mean(cv_image)
                signature['std_intensity'] = np.std(cv_image)
                
                # Create templates for template matching (multiple regions)
                h, w = cv_image.shape[:2]
                templates = []
                
                # Extract 4 corner templates and 1 center template
                template_size = min(64, min(h, w) // 4)  # Adaptive template size
                
                positions = [
                    (0, 0),  # Top-left
                    (0, w - template_size),  # Top-right
                    (h - template_size, 0),  # Bottom-left
                    (h - template_size, w - template_size),  # Bottom-right
                    (h // 2 - template_size // 2, w // 2 - template_size // 2)  # Center
                ]
                
                for y, x in positions:
                    if y >= 0 and x >= 0 and y + template_size <= h and x + template_size <= w:
                        template = cv_image[y:y + template_size, x:x + template_size]
                        templates.append(template)
                
                signature['templates'] = templates
                signature['template_size'] = template_size
            
            # Compute fuzzy hash using ssdeep
            with open(image_path, 'rb') as f:
                signature['ssdeep_hash'] = ssdeep.hash(f.read())
            
            # Compute MD5 hash for exact matching from hashlib in fuzzy hash rule.
            with open(image_path, 'rb') as f:
                signature['md5_hash'] = hashlib.md5(f.read()).hexdigest()
                
        except Exception as e:
            print(f"Warning: Error computing signature for {image_path}: {e}")
            signature['error'] = str(e)
        
        return signature
    
    def find_best_match(self, input_image_path):
        '''
        Compare input image to all targets using expert system rules and return best match for that image.
        Args: input_image_path (str): Path to input image .Returns best_match_filename, confidence_score, evidence_dict.
        '''
        if not self.targets:
            raise ValueError("No targets registered. Call register_targets() first.")
        

        try:
            input_signature = self._compute_signature(input_image_path)
        except Exception as e:
            print(f"Error processing input image {input_image_path}: {e}")
            return None, 0, {'error': str(e)}
        
        best_match = None
        best_score = 0
        best_evidence = {}
        

        for target_name, target_signature in self.targets.items():
            score, evidence = self._compare_signatures(input_signature, target_signature, target_name)
            
            if score > best_score:
                best_score = score
                best_match = target_name
                best_evidence = evidence
        
        return best_match, best_score, best_evidence
    
    def _compare_signatures(self, input_sig, target_sig, target_name) :
        '''
        Compare two image signatures(Features) using all three rules and aggregate the scores and evidence as well.
        Args: input_sig: Input image signature
              target_sig: Target image signature
              target_name: Name of target for evidence
        Returns total_score, evidence_dict
        '''
        from rules import apply_metadata_rule, apply_fuzzy_hash_rule, apply_template_matching_rule
        
        evidence = {
            'target_name': target_name,
            'rules': {}
        }
        
        total_score = 0
        
        # Rule 1: Metadata Analysis (30 points max)
        try:
            meta_score, meta_reason = apply_metadata_rule(input_sig, target_sig)
            evidence['rules']['metadata'] = {
                'score': meta_score,
                'reason': meta_reason,
                'max_score': 30
            }
            total_score += meta_score
        except Exception as e:
            evidence['rules']['metadata'] = {
                'score': 0,
                'reason': f'Error: {str(e)}',
                'max_score': 30
            }
        
        # Rule 2: Fuzzy Hashing (10 points max)
        try:
            fuzzy_score, fuzzy_reason = apply_fuzzy_hash_rule(input_sig, target_sig)
            evidence['rules']['fuzzy_hash'] = {
                'score': fuzzy_score,
                'reason': fuzzy_reason,
                'max_score': 10
            }
            total_score += fuzzy_score
        except Exception as e:
            evidence['rules']['fuzzy_hash'] = {
                'score': 0,
                'reason': f'Error: {str(e)}',
                'max_score': 10
            }
        
        # Rule 3: Template Matching (60 points max)
        try:
            template_score, template_reason = apply_template_matching_rule(input_sig, target_sig)
            evidence['rules']['template_matching'] = {
                'score': template_score,
                'reason': template_reason,
                'max_score': 60
            }
            total_score += template_score
        except Exception as e:
            evidence['rules']['template_matching'] = {
                'score': 0,
                'reason': f'Error: {str(e)}',
                'max_score': 60
            }
        
        evidence['total_score'] = total_score
        evidence['max_total_score'] = 100
        evidence['is_match'] = total_score >= 60
        
        return total_score, evidence