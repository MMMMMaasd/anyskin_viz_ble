# anyskin_viz_ble
Anyskin-to-PC visualization via bluetooth connection (bleak)

### Setup instructions
1. Create a conda environment

    ```
    conda create -n anyskin_viz python=3.11 numpy
    ```

2. Install remaining packages
    ```
    pip install -r requirements.txt
    ```

### Running instructions
1. Run visualizer python file
    ```
    python viz_one_side.py
    ```
    OR
    ```
    python viz_two_side.py
    ```
2. If you would like to make the visualization more or less sensitive, use the `-s` flag to adjust the downscaling. Default value is 7.0. Therefore, to make it _more_ sensitive, reduce s to, say, 4
    ```
    python viz_one_side.py -s 4
    ```
