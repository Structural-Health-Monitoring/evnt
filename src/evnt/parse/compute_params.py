import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import glob, os
from datetime import datetime, timedelta 
from evnt.param.asce import get_min_max_freq_range
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
    

    
class StructuralWaveforms:
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
    
    def get_waveform_statistics(self, streams=None, channel_file=None, units='acc'):
        """
        Get the waveform statistics for a channel file.
        """

        if channel_file:
            # Read the building data
            streams = self.read_building_data(channel_file, units=units)
        
        if streams is None:
            return None
        
        # Initialize the statistics dictionary
        all_stats = []
        
        for trace in streams:
            # Detrend the trace
            trace.detrend(type="linear")
            trace.detrend(type="constant")
            
            # Get the data
            data = trace[0].data

            # station information
            network = trace[0].stats['network']
            station = trace[0].stats['station']

            ## location
            latitude = trace[0].stats['coordinates']['latitude']
            longitude = trace[0].stats['coordinates']['longitude']
            elevation = trace[0].stats['coordinates']['elevation']

            # Get the start and end times
            start_time = trace[0].stats['starttime']
            end_time = trace[0].stats['endtime']
            source = trace[0].stats['standard']['source']
            source_file = trace[0].stats['standard']['source_file']
            npts = trace[0].stats['npts']
            
            # sensor_sensitivity
            sensor_sensitivity = trace[0].stats['format_specific']['sensor_sensitivity']
            scaling_factor = trace[0].stats['format_specific']['scaling_factor']
            low_filter_corner = trace[0].stats['format_specific']['low_filter_corner']
            high_filter_corner = trace[0].stats['format_specific']['high_filter_corner']
            instrument_period = trace[0].stats['standard']['instrument_period']
            instrument_damping = trace[0].stats['standard']['instrument_damping']

            # Compute the waveform statistics
            mean = self.compute_mean(data)
            standard_deviation = self.compute_standard_deviation(data)
            rms = self.compute_rms(data)
            pga = self.compute_pga(data)
            envelope = self.compute_envelope(data)
            skewness = self.compute_skewness(envelope)
            kurtosis = self.compute_kurtosis(envelope)

            # sampling_rate
            self.sampling_frequency = trace[0].stats['sampling_rate']

            #cav
            zero_crossing_rate = self.compute_zero_crossing_rate(data)
            cav = self.compute_cav(data)

            # units_type
            units_type = trace[0].stats['standard']['units_type']
            units = trace[0].stats['standard']['units']

            # orientation
            horizontal_orientation = trace[0].stats['standard']['horizontal_orientation']
            
            # Add the statistics to the dictionary
            stats = {
                # station information
                'network': network,
                'station': station,
                'channel': trace[0].stats['channel'],
                'start_time': start_time,
                'end_time': end_time,
                'npts': npts,
                'latitude': latitude,
                'longitude': longitude,
                'elevation': elevation,
                'units_type': units_type,
                'units': units,
                'source': source,
                'source_file': source_file,

                # sensor information
                'sensor_sensitivity': sensor_sensitivity,
                'scaling_factor': scaling_factor,
                'sampling_rate': self.sampling_frequency,
                'low_filter_corner': low_filter_corner,
                'high_filter_corner': high_filter_corner,
                'instrument_period': instrument_period,
                'instrument_damping': instrument_damping,

                # waveform statistics
                'mean': mean,
                'standard_deviation': standard_deviation,
                'rms': rms,
                'pga': pga,
                'skewness': skewness,
                'kurtosis': kurtosis,
                'zero_crossing_rate': zero_crossing_rate,
                'cav': cav,

                # orientation
                'horizontal_orientation': horizontal_orientation,
            }
            all_stats.append(stats)
        return all_stats


    def heaviside(self, x):
        """
        Compute the Heaviside step function H(x).
        """
        return np.where(x >= 0, 1, 0)

    def compute_pga_interval(self, interval_data):
        """
        Compute the Peak Ground Acceleration (PGA) in the given interval.
        """
        return np.max(np.abs(interval_data))  # Peak absolute acceleration
    
    def compute_cav(self, data):
        """
        Compute the standardized CAV based on the EPRI 2006 equation.
        Only intervals with PGA > 0.025g contribute to the CAV.
        """
        g_conversion = 9.81  # Convert g to m/s²
        cav_threshold = 0.025 * g_conversion  # 0.025g in m/s²

        # Number of samples per 1-second interval
        samples_per_second = int(self.sampling_frequency)
        num_intervals = len(data) // samples_per_second

        cav = 0.0

        for i in range(num_intervals):
            # Get the data for this 1-second interval
            interval_data = data[i * samples_per_second:(i + 1) * samples_per_second]

            # Compute the Peak Ground Acceleration (PGA) in this interval
            pga = self.compute_pga_interval(interval_data)

            # Apply the Heaviside function to the condition (PGA - 0.025g)
            if pga > cav_threshold: # use conditional instead of Heaviside function
                # If PGA > 0.025g, compute the integral of |a(t)| over the interval
                cav += np.trapz(np.abs(interval_data), dx=1/self.sampling_frequency)

        return cav
    
    def compute_zero_crossing_rate(self, data):
        """
        Compute the zero-crossing rate of the waveform.
        Zero-crossing rate is the number of times the signal changes sign per unit time.
        """
        zero_crossings = np.where(np.diff(np.sign(data)))[0]
        num_zero_crossings = len(zero_crossings)

        # Calculate the zero-crossing rate by normalizing by the signal duration
        signal_duration = len(data) / self.sampling_frequency  # duration in seconds
        zero_crossing_rate = num_zero_crossings / signal_duration

        return zero_crossing_rate

    def compute_mean(self, data):
        """
        Compute the mean of the waveform data.
        """
        return np.mean(data)

    def compute_standard_deviation(self, data):
        """
        Compute the standard deviation of the waveform data.
        """
        return np.std(data)

    def compute_rms(self, data):
        """
        Compute the root mean square (RMS) of the waveform data.
        """
        return np.sqrt(np.mean(np.square(data)))
    
    def compute_pga(self, data):
        """
        Compute the Peak Ground Acceleration (PGA), the maximum absolute value of the waveform data.
        """
        return np.max(np.abs(data))
    
    def compute_envelope(self, data, window_size=50):
        """
        Compute the envelope of the waveform using the Hilbert transform
        and smooth it using a moving average.
        
        Parameters:
        - window_size: Number of points to average for smoothing.
        """
        # Compute the envelope using the Hilbert transform
        analytic_signal = hilbert(data)
        envelope = np.abs(analytic_signal)
        
        # Apply a moving average for smoothing
        smooth_envelope = np.convolve(envelope, np.ones(window_size)/window_size, mode='same')
        
        return smooth_envelope

    def compute_skewness(self, envelope):
        """
        Compute the skewness of the waveform envelope.
        """
        return skew(envelope)

    def compute_kurtosis(self, envelope):
        """
        Compute the kurtosis of the waveform envelope.
        """
        return kurtosis(envelope)


    def __del__(self):
        # Ensure the zip file is closed when the object is deleted
        if self.zip_obj:
            self.zip_obj.close()
