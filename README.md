# Development

Run the following code to install all required packages
```bash
pip install --no-deps --target=./addon/libs -r requirements.txt
```

Run the following code to get a list of packages to add to requirements.txt
```bash
pip install --target=./temp/libs <package_name>
pip freeze --path=./temp/libs > temp_reqs.txt
```


