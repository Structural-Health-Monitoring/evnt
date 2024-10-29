# NOTES

- Top level read() function
- Combine QuakeComponent and QuakeSeries into one TimeSeries class
- QuakeCollection becomes collection of TimeSeries, not QuakeMotions
- no longer try to create QuakeMotion by default; instead assemble QuakeMotions using core.space.localize function