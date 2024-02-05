# Usage

Execute the script `test.js` with various arguments:

```bash
./test.js -ip '["192.168.5.151","0.0.0.0"]' -i 500 -cv 10 -f "output.csv"
```

## This command passes the following arguments:

-ip '["192.168.5.151","0.0.0.0"]': Sets the allIP to an array of IP addresses.
-i 500: Sets the interval_to_call to 500.
-cv 10: Sets the cache_values_before_writing to 10.
-f "output.csv": Sets the file_name to "output.csv".

### File_name can be absolute as follows:
./test.js -f ~/shared_fs/abc.csv