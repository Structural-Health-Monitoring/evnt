import matplotlib.pyplot as plt
import numpy as np

## Define default plot parameters for matplotlib
plt.rcParams['font.size'] = 16
plt.rcParams['axes.linewidth'] = 1.5
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['savefig.bbox'] = 'tight'

## approximate fundamental period parameters
structure_parameters_dict = {
    'seismic': {
        'steel_moment_resisting_frame': {
            'Ct': 0.028,
            'x': 0.8,
        },
        'reinforced_concrete_moment_resisting_frame': {
            'Ct': 0.016,
            'x': 0.9,
        },
        'eccentrically_braced_frame': {
            'Ct': 0.030,
            'x': 0.75,
        },
        'concrete_shear_wall': {
            'Ct': 0.020,
            'x': 0.75,
        },
        'wood_frame': {
            'Ct': 0.032,
            'x': 0.55,
        },
        'other': {
            'Ct': 0.020,
            'x': 0.75,
        },
    },

    'wind': {
        'steel_moment_resisting_frame': {
            'Ct': 0.045,
            'x': 0.8,
        },
        'reinforced_concrete_moment_resisting_frame': {
            'Ct': 0.023,
            'x': 0.9,
        },
        'other_over_400ft': {
            'Ct': 0.0067,
            'x': 1.0,
        },
        'other_below_400ft': {
            'Ct': 0.013,
            'x': 1.0,
        }
    }
}

def get_min_max_freq_range(height_in_meters, structure_type='other', force_kind='seismic'):
    # Convert the height to feet
    height = height_in_meters * 3.28084

    structure_params = structure_parameters_dict[force_kind]
    if force_kind == 'seismic':
        params = structure_params.get(structure_type, structure_params['other'])
    elif force_kind == 'wind':
        params = structure_params.get(structure_type, None)
        if params is None:
            if height > 400:
                params = structure_params['other_over_400ft']
            else:
                params = structure_params['other_below_400ft']

    # Get the parameters for the structure type
    Ct = params['Ct']
    x = params['x']

    # Calculate the approximate fundamental period
    T = Ct * (height_in_meters ** x)
    # print(f"Height: {height} meters")
    print(f"Approximate fundamental period for {structure_type}: {T:.2f} seconds or {1/T:.2f} Hz")

    # Calculate the center frequency
    f_center = 1 / T
    # Calculate f_min and f_max centered around the center frequency
    # f_min to be -n% of f_center
    # f_max to be +150% of f_center
    if height_in_meters >= 100:
        f_min = f_center - (f_center / 1.2) 
        f_max = f_center + (f_center / 10) 
    elif 70 < height_in_meters < 100:
        f_min = f_center - (f_center / 1.6) 
        f_max = f_center + (f_center / 7) 
    else:
        f_min = f_center - (f_center / 2) 
        f_max = f_center + (f_center / 3)

    if f_min < 0:
        f_min = 0.05
    
    if f_max > 5:
        f_max = 5.0
    print(f"Center frequency: {f_center:.2f} Hz | Frequency range: {f_min:.2f} - {f_max:.2f} Hz")

    return f_min, f_max

# approximate fundamental period
def approximate_fundamental_period(structure_type, height_in_meters, force_kind='seismic'):
    # Convert the height to feet
    height = height_in_meters * 3.28084
    
    structure_params = structure_parameters_dict[force_kind]
    if force_kind == 'seismic':
        params = structure_params.get(structure_type, structure_params['other'])
    elif force_kind == 'wind':
        params = structure_params.get(structure_type, None)

        if params is None:
            if height > 400:
                params = structure_params['other_over_400ft']
            else:
                params = structure_params['other_below_400ft']

    # Get the parameters for the structure type
    Ct = params['Ct']
    x = params['x']
    
    # Calculate the approximate fundamental period
    T = Ct * (height ** x)
    return T

## Plot the approximate fundamental period for different structure types
def plot_approximate_fundamental_period():
    heights = np.arange(30, 220, 10)  # in meters

    # Taipei 101's height and approximate fundamental period
    taipei_101_height = 508  # in meters
    taipei_101_T = approximate_fundamental_period('reinforced_concrete_moment_resisting_frame', taipei_101_height)
    print(f"Taipei 101's approximate fundamental period: {taipei_101_T:.2f} seconds")

    # Plot the approximate fundamental period for each structure type
    fig, ax = plt.subplots(2, 1, figsize=(12, 6), sharex=True)

    for i, force_kind in enumerate(['seismic', 'wind']):
        for j, structure_type in enumerate(structure_parameters_dict[force_kind].keys()):
            T_values = [approximate_fundamental_period(structure_type, h, force_kind=force_kind) for h in heights]
            structure_label = structure_type.replace('_', ' ').title()
            structure_color = f"C{j}"
            print(f"-- Plotting {structure_label}: {structure_color}")
            ax[i].plot(heights, 1 / np.array(T_values), label=structure_label, lw=1.5)  # frequency

            # Set the labels and title
            ax[i].legend(loc='upper left', bbox_to_anchor=(1.05, 1), fancybox=True, shadow=True)
            ax[i].grid(True)
        ax[i].set_title(f"Force Kind: {force_kind.title()}".title())

    fig.text(0.04, 0.5, 'F0 (Hz)', va='center', rotation='vertical', fontsize=16)
    ax[1].set_xlabel('Height (meters)')
    outfig = 'approximate_fundamental_frequency.png'
    plt.savefig(outfig, dpi=300, bbox_inches='tight')
    print(f"Plot saved as {outfig}")

if __name__ == "__main__":
    # Plot the approximate fundamental period
    plot_approximate_fundamental_period()
