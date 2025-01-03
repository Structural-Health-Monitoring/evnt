# `evnt`

[![PyPI Downloads][pypi-v-image]][pypi-v-link]
[![PyPI Version][pypi-d-image]][pypi-d-link]
![][cov-img]
<!-- ![Build][build-img] -->
[![Commits since latest release][gh-image]][gh-link]

`evnt` is a library of utilities for structural response parsing and health parameter extraction.

- [Install](#install)
- [Get Started](#get-started)
- [Formats](#events-parsed-using-parse-submodule)
- [Parameters](#parameters-extracted-using-param-submodule)


## Install

Run the following command:

```shell
pip install evnt
```

## Get Started

```shell
conda create --name evnt python=3.11
python -m pip install evnt
```
OR (for an editable install)
```shell
conda create --name evnt python=3.11
python -m pip install -e .
```

## Events parsed using `parse` submodule
- Bridges: Only two NSMP stations have data
- Event data for NSMP is in `.smc` or `.V2C` or `.V2` format
- Ambient data is in `.mseed` format

<!-- | Format          | Read      | Write   |  Reference              |
|-----------------|-----------|---------|-------------------------|
|`[evnt.]json` | &#9745;   | &#9745; | [schema][record-schema] |
|`csmip`          | &#9744;   | &#9744; |                         |
|`csmip.v2`       | &#9745;   | &#9744; | [CSMIP][CSMIP]          |
|`eqsig`          | &#9745;   | &#9745; | [eqsig][EQSIG]          |
|`PEER.NGA`       | &#9745;   | &#9744; |                         |
|`plain.tsv`      | &#9744;   | &#9744; |                         |
|`opensees`       | &#9744;   | &#9745; |                         |
|`plain.csv`      | &#9744;   | &#9744; |                         |
|`mdof`           | &#9744;   | &#9744; |                         |
| SimCenter.Event | &#9744;   | &#9744; |                         | -->


## Parameters extracted using `param` submodule

### Time Domain (Single Channel)
1. __Waveform Duration__: The total time span from the beginning to the end of the recorded waveform
1. __Mean__: The average value of the acceleration waveform over time, calculated as the sum of all acceleration values divided by the number of samples. This provides a measure of the waveform's central tendency.
1. __Standard Deviation__: A statistical measure of the waveform's variability or spread. It quantifies the amount of variation or dispersion of the acceleration values from the mean. Higher values indicate greater variability in the waveform.
1. __RMS (Root Mean Square) Amplitude__: The square root of the mean of the squared acceleration values. This gives a measure of the overall energy or power of the waveform, effectively smoothing out both positive and negative acceleration values.
1. __Peak Ground Acceleration (PGA)__: The maximum absolute value of the ground acceleration in the waveform, typically representing the highest level of shaking experienced at a site during a seismic event. It is often used to assess the potential for structural damage.
1. __Skewness of the Waveform Envelope__: Skewness quantifies the asymmetry in the distribution of the amplitude values of the waveform's envelope, computed using the Hilbert transform. A positive skewness indicates that the envelope is dominated by large peaks, meaning the energy is concentrated in short bursts, while negative skewness suggests more prolonged low-amplitude sections in the waveform.
1. __Kurtosis__: Kurtosis measures the "peakedness" or "tailedness" of the amplitude distribution of the waveform's envelope. High kurtosis reflects that the envelope is dominated by sharp, high-amplitude peaks, indicating potential impulsive energy, while low kurtosis signifies a more uniform distribution of energy without extreme values.
1. __Zero-Crossing Rate__: The number of times the waveform crosses the zero amplitude axis per unit time. A higher zero-crossing rate indicates greater frequency content or signal complexity, while a lower rate suggests lower-frequency content.
1. __Arias Intensity__: A cumulative measure of the energy content of the waveform, calculated by integrating the square of the acceleration over time. It is often used to assess the potential for structural damage and is related to the total seismic energy imparted to a structure or site.
1. __Cumulative Absolute Velocity (CAV)__: The cumulative integral of the absolute acceleration values over time, typically used in seismic hazard analysis to assess the overall intensity of ground shaking. It helps quantify the damage potential for structures and is particularly useful for assessing cumulative effects over prolonged shaking periods.

### Time Domain (Multiple channels)
1. __H/V Ratio (Horizontal to Vertical Spectral Ratio)__: The ratio of the spectral amplitudes of the horizontal and vertical components of ground motion. This ratio is commonly used to estimate local site effects and resonance characteristics, as well as to identify potential amplification of seismic waves due to geological conditions.

### Time Domain (Building)
1. Interstory Drift (Max displacement! or Mean??)
1. Residual Drift!

### Frequency Domain
1. __Dominant Frequency__: The frequency at which the waveform exhibits the highest amplitude in its power spectrum. This is the primary frequency of oscillation in the waveform and often reflects the main resonance or response of the ground or structure.
1. __Amplitude at the Dominant Frequency__: The value of the waveform's amplitude at the dominant frequency, providing insight into the strength of the signal at its most prominent frequency. This can help assess the magnitude of shaking related to specific frequency components.
1. __Signal-to-Noise Ratio (SNR)__: The SNR is calculated as the ratio of the peak power at the dominant frequency (the frequency with the highest amplitude in the power spectrum) to the average power of the waveform in the frequency range before the dominant frequency. This ratio gives an indication of how strong the signal is at the dominant frequency relative to the noise or less significant frequency components preceding it. Higher SNR indicates clearer signal quality at the dominant frequency, whereas lower SNR reflects a less prominent frequency amidst background noise.
1. __Damping Ratio__: A dimensionless measure of how oscillations in a system decay after a disturbance. In the context of a seismic signal, it quantifies how quickly the shaking reduces over time. It is a critical parameter in understanding how buildings or structures respond to seismic waves.

<!-- Reference links -->
[EQSIG]: https://github.com/eng-tools/eqsig
[CSMIP]: https://www.conservation.ca.gov/cgs/Documents/Program-SMIP/Reports/Other/OSMS_85-03.pdf
[record-schema]: https://raw.githubusercontent.com/claudioperez/evnt/master/etc/schemas/record.schema.json

<!-- Badge links -->
[pypi-d-image]: https://img.shields.io/pypi/dm/evnt.svg
[license-badge]: https://img.shields.io/pypi/l/evnt.svg
[pypi-d-link]: https://pypi.org/project/evnt
[pypi-v-image]: https://img.shields.io/pypi/v/evnt.svg
[pypi-v-link]: https://pypi.org/project/evnt
[build-img]: https://github.com/claudioperez/evnt/actions/workflows/base.yml/badge.svg
[cov-img]: https://raw.githubusercontent.com/claudioperez/evnt/master/etc/coverage/cov.svg
[gh-link]: https://github.com/structural-health-monitoring/evnt
[gh-image]: https://img.shields.io/github/commits-since/claudioperez/evnt/v0.1.14?style=social