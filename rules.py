import cv2
import numpy as np
import ssdeep

'''
    Rule 1: Metadata Analysis compares key image properties:
    - File size
    - Dimensions
    - Mode
    
    Args:
        original_size: Metadata of the input image
        input_size: Metadata of the target image
        
    Returns score, reason_string for 30 points max.
    '''

def apply_metadata_rule(original_size, input_size):

    score = 0
    reasons = []
    
    # Check file size ratio (up to 10 points)
    if 'file_size' in original_size and 'file_size' in input_size:
        original_input = original_size['file_size']
        target_size = input_size['file_size']
        size_ratio = min(original_input, target_size) / max(original_input, target_size)
        
        if size_ratio > 0.9:
            size_score = 10
        elif size_ratio > 0.7:
            size_score = 8
        elif size_ratio > 0.5:
            size_score = 4
        else:
            size_score = 0
            
        score += size_score
        reasons.append(f"Size ratio {size_ratio:.3f} -> {size_score}/10 pts") 

    
    # Check dimensions ratio (up to 12 points)
    if 'dimensions' in original_size and 'dimensions' in input_size:
        input_dims = original_size['dimensions']
        target_dims = input_size['dimensions']
        
        '''Calculate area ratio

        Area = Width * Height
        Area Ratio=Area of Smaller Image/Area of Smaller Image
        '''
        input_area = input_dims[0] * input_dims[1]
        target_area = target_dims[0] * target_dims[1]
        area_ratio = min(input_area, target_area) / max(input_area, target_area)
        
        '''
        Calculate aspect ratio similarity
        Aspect Ratio = Height/Width
        '''
        input_aspect = input_dims[0] / input_dims[1]
        target_aspect = target_dims[0] / target_dims[1]
        aspect_diff = abs(input_aspect - target_aspect) / max(input_aspect, target_aspect)
        
        if area_ratio > 0.8 and aspect_diff < 0.1:
            dim_score = 12
        elif area_ratio > 0.6 and aspect_diff < 0.2:
            dim_score = 9
        elif area_ratio > 0.4:
            dim_score = 6
        else:
            dim_score = 0
            
        score += dim_score
        reasons.append(f"Dimension similarity {area_ratio:.3f} -> {dim_score}/12 pts")
    
    # Check image mode compatibility (up to 8 points)
    if 'mode' in original_size and 'mode' in input_size:
        input_mode = original_size['mode']
        target_mode = input_size['mode']
        
        if input_mode == target_mode:
            mode_score = 8
            reasons.append(f"Mode match ({input_mode}) -> 8/8 pts")
        elif (input_mode in ['RGB', 'RGBA'] and target_mode in ['RGB', 'RGBA']) :
            mode_score = 4
            reasons.append(f"Mode compatible ({input_mode}/{target_mode}) -> 4/8 pts")
        else:
            mode_score = 0
            reasons.append(f"Mode mismatch ({input_mode}/{target_mode}) -> 0/8 pts")
            
        score += mode_score
    
    # Ensure score doesn't exceed maximum
    score = min(score, 30)
    
    # Determine if rule fired
    if score >= 15:  # At least 50% of max score
        status = "FIRED"
    else:
        status = "NO MATCH"
    
    reason = f"{status} - {', '.join(reasons)}"
    
    return score, reason


def apply_fuzzy_hash_rule(original_size, input_size):
    '''
    Rule 2: Fuzzy Hashing - Use ssdeep to detect file-level similarity.
    This rule is less effective for images due to compression and cropping,
    but can still catch some modifications.
    
    Args:
        original_size: Input image signature
        input_size: Target image signature

    Returns score, reason_string for 10 points max.
    '''
    score = 0
    
    if 'ssdeep_hash' in original_size and 'ssdeep_hash' in input_size:
        input_hash = original_size['ssdeep_hash']
        target_hash = input_size['ssdeep_hash']
        
        try:
            # Compare ssdeep hashes
            similarity = ssdeep.compare(input_hash, target_hash)
            
            # Score based on similarity percentage
            # Note: ssdeep is not very effective for images, especially cropped/compressed ones
            if similarity >= 80:
                score = 10
                status = "STRONG MATCH"
            elif similarity >= 60:
                score = 8
                status = "MATCH"
            else:
                score = 0
                status = "NO MATCH"
                
            reason = f"{status} - ssdeep similarity {similarity}%"
            
        except Exception as e:
            score = 0
            reason = f"NO MATCH - ssdeep error: {str(e)}"
    else:
        score = 0
        reason = "NO MATCH - ssdeep hash unavailable"
    
    return score, reason


def apply_template_matching_rule(original_size, input_size):
    '''
    Rule 3: Template Matching - Use OpenCV to detect visual similarity.
    
    This rule is particularly effective for detecting crops and visual modifications from the modified image.
    It uses multiple templates from different regions of the original image.
    
    Args:
        original_size: Input image signature
        input_size: Target image signature
        
    Returns score, reason_string for 60 points max.
    '''
    score = 0
    
    if 'templates' not in input_size or not input_size['templates']:
        return 0, "NO MATCH - no templates available"
    
    try:
        # Load input image for template matching
        input_path = original_size.get('path')
        if not input_path:
            return 0, "NO MATCH - input path unavailable"
        
        input_image = cv2.imread(input_path)
        if input_image is None:
            return 0, "NO MATCH - cannot load input image"
        
        target_templates = input_size['templates']
        best_matches = []
        
        # Test each template from the target image
        for i, template in enumerate(target_templates):
            if template is None or template.size == 0:
                continue
                
            try:
                # Perform template matching
                result = cv2.matchTemplate(input_image, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)
                best_matches.append(max_val)
                
            except Exception as e:
                # Template might be too large for input image
                continue
        
        if not best_matches:
            return 0, "NO MATCH - no valid template matches"
        
        # Use the best match value
        best_match = max(best_matches)
        avg_match = np.mean(best_matches)
        
        
        # Scoring based on match quality and consistency
        if best_match >= 0.9 and avg_match >= 0.7:
            score = 60  # Perfect match
            status = "EXACT MATCH"
        elif best_match >= 0.8 and avg_match >= 0.6:
            score = 50
            status = " GOOD MATCH"
        elif best_match >= 0.7 and avg_match >= 0.5:
            score = 45
            status = " MATCH"
        else:
            score = 0
            status = "NO MATCH"
        
    
        
        reason = f"{status} - OpenCV match {best_match:.3f} (avg: {avg_match:.3f})"
        
    except Exception as e:
        score = 0
        reason = f"NO MATCH - template matching error: {str(e)}"
    
    return score, reason


def combine_rule_scores(metadata_score, fuzzy_score, template_score) :
    '''
    Combine scores from all three rules scores to determine final match decision.
    
    Args:
        metadata_score: Score from metadata rule (0-30)
        fuzzy_score: Score from fuzzy hash rule (0-10)  
        template_score: Score from template matching rule (0-60)
        
    Returns total_score, is_match (boolean)
    '''
    total_score = metadata_score + fuzzy_score + template_score
    is_match = total_score >= 60
    
    return total_score, is_match