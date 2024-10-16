import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import glob, os
from datetime import datetime, timedelta 
from evnt.param.asce_7_fundamental_period import get_min_max_freq_range
import multitaper.mtspec as spec
import matplotlib.dates as mdates
from scipy.interpolate import interp1d 
from scipy.signal import hilbert
from scipy.stats import skew, kurtosis
import zipfile
from gmprocess.io.dmg.core import read_dmg
import tempfile
import logging

# Set the logging level to ERROR to suppress WARNING messages
logging.getLogger().setLevel(logging.ERROR)

plt.style.use('ggplot')

# plt.rcParams.update({'font.size': 22})
plt.rcParams.update({'font.size': 16})
    

    
class GMProcessWaveforms:
    available_formats = ('.V1','.V2','.V3')
    
    def __init__(self, smc_zip_file: str) -> None:
        self.smc_zip_file = smc_zip_file
        self.zip_obj = zipfile.ZipFile(smc_zip_file, 'r')  # Open the zip file
        self.parser = None

    def get_all_channel_files(self, format_type: str = None):
        if format_type is None:
            for ftype in self.available_formats:
                # List all files in the zip archive that match the format
                all_chan_data = [f for f in self.zip_obj.namelist() if f.endswith(ftype)]

                all_chan_data.sort()
                # print(f"Total channel files with format {ftype}: {len(all_chan_data)}")
                if len(all_chan_data) > 0:
                    return all_chan_data, ftype
        else:
            # List all files in the zip archive that match the format
            all_chan_data = [f for f in self.zip_obj.namelist() if f.endswith(format_type)]

            all_chan_data.sort()
            if len(all_chan_data) > 0:
                return all_chan_data, format_type
                    
        ## if length of all_chan_data is 0, then suggest the available formats in the zip file from available_formats
        if len(all_chan_data) == 0:
            # print(f"-- No files found with format {format_type}. Available formats: {self.available_formats}")
            return [], None

    def read_building_data(self, channel_file: str = None, units: str = 'acc'):
        if channel_file is None:
            # Get the first channel file from the zip
            channel_file = self.get_all_channel_files()[0]

        try:
            # Extract the channel file to a temporary location
            with tempfile.TemporaryDirectory() as temp_dir:
                extracted_path = os.path.join(temp_dir, channel_file)
                
                # Extract the file
                with open(extracted_path, 'wb') as extracted_file:
                    extracted_file.write(self.zip_obj.read(channel_file))
                
                # Read the extracted file using read_dmg
                strm = read_dmg(extracted_path, config=None, units=units)
        except BaseException as e:
            # Catch the specific error related to the DMG header and continue
            if "DMG: Not enough information to distinguish horizontal from vertical channels" in str(e):
                print(f"Skipping file due to channel error: {channel_file}")
                strm = None
            else:
                # Re-raise other BaseExceptions
                raise e
        except Exception as e:
            # Handle other exceptions
            print(f"Error reading {channel_file}: {e}")
            strm = None

        return strm


    def __del__(self):
        # Ensure the zip file is closed when the object is deleted
        if self.zip_obj:
            self.zip_obj.close()
