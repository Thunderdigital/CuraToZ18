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
        source_img_path = os.path