
import os
import sys
import time
from forensics_detective import SimpleDetective

def format_output(filename, evidence):
    '''
    Format the output according to the required command line format.
    
    Args:
        filename: Name of the processed file/image
        evidence: Evidence dictionary from find_best_match
    Returns Formatted output string as required and to output file also.
    '''
    lines = [f"Processing: {filename}"]
    
    # Rule 1: Metadata
    if 'metadata' in evidence['rules']:
        meta = evidence['rules']['metadata']
        lines.append(f"Rule 1 (Metadata): {meta['reason']} -> {meta['score']}/{meta['max_score']} points")
    else:
        lines.append("Rule 1 (Metadata): ERROR -> 0/30 points")
    
    # Rule 2: Fuzzy Hash
    if 'fuzzy_hash' in evidence['rules']:
        fuzzy = evidence['rules']['fuzzy_hash']
        lines.append(f"Rule 2 (Fuzzy Hash): {fuzzy['reason']} -> {fuzzy['score']}/{fuzzy['max_score']} points")
    else:
        lines.append("Rule 2 (Fuzzy Hash): ERROR -> 0/10 points")
    
    # Rule 3: Template Matching
    if 'template_matching' in evidence['rules']:
        template = evidence['rules']['template_matching']
        lines.append(f"Rule 3 (Template): {template['reason']} -> {template['score']}/{template['max_score']} points")
    else:
        lines.append("Rule 3 (Template): ERROR -> 0/60 points")
    
    # Checks if match or not with final score and target name if matched.
    total_score = evidence.get('total_score', 0)
    if evidence.get('is_match', False):
        lines.append(f"Final Score: {total_score}/100 -> MATCH to {evidence.get('target_name', 'unknown')}")
    else:
        lines.append(f"Final Score: {total_score}/100 -> REJECTED")
    
    return '\n'.join(lines) + '\n'

def test_system(originals_folder, modified_folder, random_folder, 
                output_file = "results.txt"):
    '''
    Test the expert system on all images and generate results.
    
    Args:
        originals_folder: Path to original images
        modified_folder: Path to modified images
        random_folder: Path to random images
        output_file: Empty Output file for results. if not will clear the existing data and write new results.
    Returns Dictionary with test statistics
    '''
    print("="*60)
    print(" Forensics Detective (Expert System)")
    print("="*60)
    
    # Initialize the detective system
    detective = SimpleDetective()
    
    # Register original images
    try:
        detective.register_targets(originals_folder)
    except Exception as e:
        print(f"Error registering targets: {e}")
        return {'error': str(e)}
    
    # Collect all test images
    test_images = []
    
    # verifies the modified images in folder 
    if os.path.exists(modified_folder):
        for filename in sorted(os.listdir(modified_folder)):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                test_images.append({
                    'path': os.path.join(modified_folder, filename),
                    'filename': filename,
                    'type': 'modified',
                    'expected_match': True
                })
    
    # verifies the random images in folder
    if os.path.exists(random_folder):
        for filename in sorted(os.listdir(random_folder)):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                test_images.append({
                    'path': os.path.join(random_folder, filename),
                    'filename': filename,
                    'type': 'random',
                    'expected_match': False
                })
    
    print(f"Testing on {len(test_images)} images...")
    print(f"- Modified images: {len([img for img in test_images if img['type'] == 'modified'])}")
    print(f"- Random images: {len([img for img in test_images if img['type'] == 'random'])}")
    print()
    
    # Test each image and collect results.
    results = []
    correct_predictions = 0
    modified_correct = 0
    random_correct = 0
    
    #to calculate the time taken to process all images. satrts the timer.
    start_time = time.time()

    # opens the output file write mode for writing results for each image processed
    with open(output_file, 'w') as f:
        f.write(" Digital Forensics Results\n")
        f.write("="*30 + "\n\n")
        
        for i, test_img in enumerate(test_images):
            print(f"Processing {i+1}/{len(test_images)}: {test_img['filename']}", end=" ... ")
            
            try:
                # Find best match
                best_match, confidence, evidence = detective.find_best_match(test_img['path'])
                
                # Determine if prediction is correct
                predicted_match = confidence >= 60
                is_correct = predicted_match == test_img['expected_match']
                
                if is_correct:
                    correct_predictions += 1
                    if test_img['type'] == 'modified':
                        modified_correct += 1
                    else:
                        random_correct += 1
                
                # Store result
                result = {
                    'filename': test_img['filename'],
                    'type': test_img['type'],
                    'expected_match': test_img['expected_match'],
                    'predicted_match': predicted_match,
                    'confidence': confidence,
                    'best_match': best_match,
                    'is_correct': is_correct,
                    'evidence': evidence
                }
                results.append(result)
                
                # Write formatted output
                formatted_output = format_output(test_img['filename'], evidence)
                f.write(formatted_output + "\n")
                
                
                print(f"Score: {confidence}/100")
                
            except Exception as e:
                print(f"ERROR: {e}")
                f.write(f"Processing: {test_img['filename']}\n")
                f.write(f"ERROR: {str(e)}\n\n")
                
                results.append({
                    'filename': test_img['filename'],
                    'type': test_img['type'],
                    'expected_match': test_img['expected_match'],
                    'predicted_match': False,
                    'confidence': 0,
                    'best_match': None,
                    'is_correct': False,
                    'error': str(e)
                })
    
    end_time = time.time() # ends the timer.
    
    # Calculate summary statistics and accuracies.
    total_images = len(test_images)
    modified_images = len([img for img in test_images if img['type'] == 'modified'])
    random_images = len([img for img in test_images if img['type'] == 'random'])
    
    overall_accuracy = (correct_predictions / total_images) * 100 if total_images > 0 else 0
    modified_accuracy = (modified_correct / modified_images) * 100 if modified_images > 0 else 0
    random_accuracy = (random_correct / random_images) * 100 if random_images > 0 else 0
    
    false_positive_rate = ((random_images - random_correct) / random_images) * 100 if random_images > 0 else 0
    
    # Prints formated summary
    print("\n" + "-"*45)
    print(" "*17 + "RESULTS SUMMARY")
    print("-"*45)
    print(f"Total images processed: {total_images}")
    print(f"Processing time: {end_time - start_time:.2f} seconds")
    print()
    print(f"Overall accuracy: {overall_accuracy:.1f}% ({correct_predictions}/{total_images})")
    print(f"Modified images accuracy: {modified_accuracy:.1f}% ({modified_correct}/{modified_images})")
    print(f"Random images accuracy: {random_accuracy:.1f}% ({random_correct}/{random_images})")
    print(f"False positive rate: {false_positive_rate:.1f}%")
    print()
    
    # calculate the scoure for each rule across all results.
    def extract_scores(results, rule_name):
    
        return [
            r["evidence"]["rules"][rule_name]["score"]
            for r in results
            if "evidence" in r 
            and "rules" in r["evidence"] 
            and rule_name in r["evidence"]["rules"]
        ]

    
    metadata_scores = extract_scores(results, "metadata")
    fuzzy_scores = extract_scores(results, "fuzzy_hash")
    template_scores = extract_scores(results, "template_matching")

    if metadata_scores:
        print(f"Metadata Rule - Avg: {sum(metadata_scores)/len(metadata_scores):.1f}/30, Max: {max(metadata_scores)}/30")
    if fuzzy_scores:
        print(f"Fuzzy Hash Rule - Avg: {sum(fuzzy_scores)/len(fuzzy_scores):.1f}/10, Max: {max(fuzzy_scores)}/10")
    if template_scores:
        print(f"Template Matching Rule - Avg: {sum(template_scores)/len(template_scores):.1f}/60, Max: {max(template_scores)}/60")
    
    print(f"\nResults written to: {output_file}")
    
    return {
        'total_images': total_images,
        'correct_predictions': correct_predictions,
        'overall_accuracy': overall_accuracy,
        'modified_accuracy': modified_accuracy,
        'random_accuracy': random_accuracy,
        'false_positive_rate': false_positive_rate,
        'processing_time': end_time - start_time,
        'results': results
    }

def main():
    '''Main function to run the test system.'''
    
    '''
    folders given as command line arguments or defaults.
    '''
    originals_folder = "originals"
    modified_folder = "modified"
    random_folder = "random"
    
    # Check command line arguments
    if len(sys.argv) > 1:
        originals_folder = sys.argv[1]
    if len(sys.argv) > 2:
        modified_folder = sys.argv[2]
    if len(sys.argv) > 3:
        random_folder = sys.argv[3]
    
    # Verify folders exist
    missing_folders = []
    for folder, name in [(originals_folder, "originals"), (modified_folder, "modified"), (random_folder, "random")]:
        if not os.path.exists(folder):
            missing_folders.append(name)
    
    if missing_folders:
        print(f"Error: Missing folders: {', '.join(missing_folders)}")
        print("Usage: python test_system.py [originals_folder] [modified_folder] [random_folder]")
        print("Default folders: originals/, modified/, random/")
        return
    
    # Run the test system
    stats = test_system(originals_folder, modified_folder, random_folder)
    
    if 'error' in stats:
        print(f"System error: {stats['error']}")
        return

if __name__ == "__main__":
    main()