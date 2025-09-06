# A2A Setup

## Step 1
*required python 3.10 or higher

### Clone the A2A samples repository

```bash
git clone https://github.com/a2aproject/a2a-samples.git -b main --depth 1
cd a2a-samples
```

## Step 2
### Create and activate virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install needed python dependencies along with the A2A SDK and its dependencies
```bash
pip install -r samples/python/requirements.txt
```

### Verify installation
```bash
python3 -c "import a2a; print('A2A SDK imported successfully')"
```
