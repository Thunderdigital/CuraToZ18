import zipfile
import os
import shutil
import tempfile
import stat
import sys
from PIL import Image

def modify_makerbot_file(file_path):
    """
    Unzips a .makerbot file, modifies configuration files (meta.json, print.jsontoolpath),
    adjusts and cleans up thumbnails (using letterbox/padding), deletes unnecessary
    files (slicemetadata.json), re-zips the content, and cleans up the temporary folder.
    """
    temp_dir = tempfile.mkdtemp()
    print(f"Created temporary working directory: {temp_dir}")
    
    # Thumbnail parameters
    source_img_name = "isometric_thumbnail_320x320.png"
    target_width, target_height = 320, 200
    new_img_name = "thumbnail_320x200.png"
    new_img_path = os.path.join(temp_dir, new_img_name)
    
    try:
        # 1. Unzip the file
        print(f"Starting unzipping: {file_path} -> {temp_dir}")
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        print("Unzipping successful.")
        
        # ----------------------------------------------------------------------
        ## Modify meta.json
        # ----------------------------------------------------------------------
        meta_json_path = os.path.join(temp_dir, "meta.json")
        if os.path.exists(meta_json_path):
            print("Modifying meta.json...")
            with open(meta_json_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # REQUIRED MODIFICATIONS for Z18 compatibility
            content = content.replace("lava_f", "z18_6")
            content = content.replace("mk14", "mk13")
            # NEW CHANGE: Replace build_plane_temperature with chamber_temperature
            content = content.replace("build_plane_temperature", "chamber_temperature") 

            with open(meta_json_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("meta.json successfully modified.")
        
        # ----------------------------------------------------------------------
        ## Modify print.jsontoolpath (Fine-tuning Header)
        # ----------------------------------------------------------------------
        print_json_path = os.path.join(temp_dir, "print.jsontoolpath")
        if os.path.exists(print_json_path):
            print("Modifying print.jsontoolpath (cleaning header, reverse search for temp commands)...")
            with open(print_json_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Markers for the commands we need to keep and the section that must remain
            set_temp_marker = '{"command":{"function":"set_toolhead_temperature"'
            wait_temp_marker = '{"command":{"function":"wait_for_temperature"'
            remaining_marker = '{"command":{"function":"comment","metadata":{},"parameters":{"comment":"Layer Section 0 (0)"},"tags":[]}},'
            
            start_bracket_index = content.find('[')
            remaining_marker_index = content.find(remaining_marker)
            
            # 1. Reverse search for the 'wait_for_temperature' (closest to Layer Section 0)
            wait_temp_index = content.rfind(wait_temp_marker, 0, remaining_marker_index)
            
            if (start_bracket_index != -1 and wait_temp_index != -1 and remaining_marker_index != -1):
                
                # 2. Reverse search for the closest 'set_toolhead_temperature'
                set_temp_index = content.rfind(set_temp_marker, 0, wait_temp_index)

                if set_temp_index != -1:
                    
                    # 3. Calculate the end of the command pair (end of the 'wait_for_temperature' command)
                    end_of_command_pair = content.find('}},', wait_temp_index) + 3 
                    
                    # The command pair to keep
                    command_pair_to_keep = content[set_temp_index:end_of_command_pair]

                    # A. Rebuild content: [ + newline + kept pair + rest of the content (from Layer Section 0)
                    new_content = content[:start_bracket_index] + '[' + '\n' + command_pair_to_keep + content[end_of_command_pair:]
                    content = new_content

                    # Re-find positions for the deletion of the middle part
                    wait_temp_index = content.rfind(wait_temp_marker, 0, content.find(remaining_marker))
                    end_of_command_pair = content.find('}},', wait_temp_index) + 3
                    remaining_marker_index = content.find(remaining_marker, end_of_command_pair)

                    # B. Delete the MIDDLE section: Between the kept pair and the Layer Section 0 command
                    start_deletion_pos = end_of_command_pair
                    end_deletion_pos = remaining_marker_index
                    
                    section_to_delete = content[start_deletion_pos:end_deletion_pos]
                    content = content.replace(section_to_delete, '')
                    
                    # C. Format JSON (add newlines between commands for readability)
                    content = content.replace('},{', '},\n{')
                    
                    print("Temperature command pair kept, other header commands deleted and formatted.")
                else:
                    print("WARNING: 'set_toolhead_temperature' not found before 'wait_for_temperature'. Deletion skipped.")
            else:
                print("WARNING: Header markers ([, wait, comment) not found as expected. Deletion skipped.")
            
            # Delete redundant 'b' attributes
            content = content.replace('"b":0.0,', '')
            content = content.replace('"b":true,', '')

            with open(print_json_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("print.jsontoolpath successfully saved.")

        # ----------------------------------------------------------------------
        ## Modify Thumbnails (Letterbox/Padding Logic)
        # ----------------------------------------------------------------------
        
        print("Processing thumbnails (scaling to fit and adding padding)...")
        source_img_path = os.path.join(temp_dir, source_img_name)

        if os.path.exists(source_img_path):
            try:
                # Load image and convert to RGB 
                img = Image.open(source_img_path).convert("RGB")
                original_width, original_height = img.size

                # Scale the image proportionally to fit the TARGET_HEIGHT (200px)
                if original_height > target_height:
                    # Since the source is 320x320, this will result in a 200x200 image.
                    scaled_width = int(original_width * (target_height / original_height))
                    scaled_height = target_height
                    img_rescaled = img.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
                else:
                    img_rescaled = img
                    scaled_width, scaled_height = original_width, original_height

                # Create new canvas with BLACK background
                canvas_img = Image.new('RGB', (target_width, target_height), color = 'black')
                
                # Calculate the position to center the scaled image (letterbox)
                x_position = (target_width - scaled_width) // 2
                y_position = (target_height - scaled_height) // 2

                # Paste the scaled image onto the canvas
                canvas_img.paste(img_rescaled, (x_position, y_position))

                # Save as the new 320x200 PNG
                canvas_img.save(new_img_path)
                print(f"Created a {target_width}x{target_height} thumbnail with padding ({new_img_name}).")
                
            except Exception as e:
                print(f"ERROR during image modification: {e}")
        else:
            print(f"WARNING: The file '{source_img_name}' was not found. Thumbnail modification skipped.")
            
        # ----------------------------------------------------------------------
        ## File Cleanup (Deletion)
        # ----------------------------------------------------------------------
        
        # 1. Delete slicemetadata.json
        slicemetadata_path = os.path.join(temp_dir, "slicemetadata.json")
        if os.path.exists(slicemetadata_path):
            os.remove(slicemetadata_path)
            print("slicemetadata.json successfully deleted.")
        
        # 2. Delete redundant 'thumbnail_' files
        files_to_keep = {new_img_name, source_img_name, "meta.json", "print.jsontoolpath"} 
        
        for file_name in os.listdir(temp_dir):
            if file_name.startswith("thumbnail_") and file_name not in files_to_keep:
                file_path_to_delete = os.path.join(temp_dir, file_name)
                try:
                    os.remove(file_path_to_delete)
                    print(f"Deleted: {file_name}")
                except OSError as e:
                    print(f"ERROR while deleting file ({file_name}): {e}")

        # 3. Re-zip and Overwrite
        print(f"Starting re-zipping and overwriting: {file_path}")
        temp_zip_name = file_path + ".temp"
        
        with zipfile.ZipFile(temp_zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path_to_zip = os.path.join(root, file)
                    zipf.write(file_path_to_zip, os.path.relpath(file_path_to_zip, temp_dir))
        
        os.replace(temp_zip_name, file_path)
        print("Re-zipping and overwriting successful.")
        
    except Exception as e:
        print(f"An error occurred during the process: {e}")
        
    finally:
        # 4. Delete Temporary Directory
        def on_rm_error(func, path, exc_info):
            os.chmod(path, stat.S_IWRITE)
            os.unlink(path)

        print(f"Deleting temporary directory: {temp_dir}")
        try:
            shutil.rmtree(temp_dir, onerror=on_rm_error)
            print("Temporary directory successfully deleted.")
        except Exception as e:
             print(f"ERROR while deleting temporary directory: {e}")
             
# ----------------------------------------------------------------------
## Program Execution
# ----------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("---------------------------------------------------------")
        print("ERROR: Please specify the .makerbot file to process!")
        print("Usage: python CuraToZ18.py <filename.makerbot>")
        print("---------------------------------------------------------")
        input("Press Enter to exit...")
        sys.exit(1)
        
    file_name = sys.argv[1]
    
    if os.path.exists(file_name):
        modify_makerbot_file(file_name)
        print("\n*** Operation completed. ***")
    else:
        print(f"ERROR: The file '{file_name}' was not found in the current directory.")
        
    # --- FINAL INPUT TO PAUSE THE CONSOLE ---
    input("Press Enter to close the window...")
    sys.exit(0)