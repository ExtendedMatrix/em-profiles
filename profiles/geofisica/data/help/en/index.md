# Geophysics

The slices, sections and volumes of a geophysical survey — GPR, ERT,
magnetometry — brought into the graph as **documents**:

- a **stack** is an acquisition (`DTCAcquisitionNode`), each source file its
  resource;
- each **slice** (a depth band) or **section** (a vertical profile) is a
  document: role *analytical*, content *2d object*, geometry from whoever says
  where it lies (*reality based* from the instrument, *observable* from a plan
  or a figure, *asserted* by eye);
- an **anomaly** you read on a slice becomes a **USD** unit with its
  **extractor** (one slice) or **combiner** (several slices). The package
  brings the measurements in and helps you trace; the archaeological judgement
  stays yours.

**Tracing.** In the Space, the three tools *point*, *linear* and *areal anomaly
on a slice* draw on the planes of a stack: a click on a slice is a point of
the anomaly. Clicks on two slices, or the slices shown «up to» the cursor,
make one extractor per slice and a combiner of them. The kind (point, linear,
areal, diffraction hyperbola, high or low resistivity) says the shape read,
not what it is. One undo step takes it all back.

Every image the package derives (a slice's PNG, the cache, a drape) is written
with its **stamp** beside it (`<file>.stamp.json`): what it was made from, how,
by which version.
