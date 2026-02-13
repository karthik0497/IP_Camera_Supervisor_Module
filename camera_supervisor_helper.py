
def get_input(prompt, default=None):
    text = f"{prompt}"
    if default:
        text += f" (default: {default})"
    text += ": "
    val = input(text)
    return val if val else default

def load_data_from_yaml(file_path: str):
    import yaml
    try:
        with open(file_path) as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
        return data
    except Exception as e:
        print(f"load_data_from_yaml FAILED [{e}]")
    return None
