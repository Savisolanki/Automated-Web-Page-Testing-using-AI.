from flask import Flask, render_template, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import requests
import json
import re
import random

app = Flask(__name__)

# Initialize global driver
driver = None

def initialize_driver():
    """Initializes the Chrome WebDriver if not already running."""
    global driver
    if driver is None:  # Check if the driver is not already initialized
        chrome_options = Options()
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--allow-insecure-localhost')
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

def extract_labels(url):
    try:
        # Initialize driver once
        driver = initialize_driver()
        driver.get(url)
        
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "form")))

        forms = driver.find_elements(By.TAG_NAME, 'form')
        labels_data = []
        labels_dict = {}

        for i, form in enumerate(forms, start=1):
            form_labels = [] 
            labels = form.find_elements(By.TAG_NAME, 'label')
            for label in labels:
                label_text = label.text.strip()
                split_label = re.split(r'\/', label_text)
                label_text = split_label[-1].strip()
                label_for = label.get_attribute('for')
                if label_for:
                    try:
                        associated_element = form.find_element(By.ID, label_for)
                        if associated_element.tag_name in ['input', 'select', 'textarea']:
                            form_labels.append(f"{label_text}")
                            labels_dict[label_text] = associated_element
                        else:
                            print(f"Label '{label_text}' has 'for' attribute, but associated element type '{associated_element.tag_name}' is not supported.")
                    except NoSuchElementException:
                        print(f"Label '{label_text}' with 'for={label_for}' was not found.")
                        continue

            inputs = form.find_elements(By.XPATH, './/input | .//select | .//textarea')
            for input_field in inputs:
                label_texts = []
                input_id = input_field.get_attribute('id')
                if not input_id:
                    if input_field.get_attribute('placeholder'):
                        label_texts.append(input_field.get_attribute('placeholder'))
                    elif input_field.get_attribute('aria-label'):
                        label_texts.append(input_field.get_attribute('aria-label'))
                    elif input_field.get_attribute('title'):
                        label_texts.append(input_field.get_attribute('title'))

                for label in label_texts:
                    labels_dict[label] = input_field

            if not form_labels:
                form_labels.append("No labels found")

            labels_data.append((i, form_labels))

        print(labels_dict)
        return labels_data, labels_dict

    except TimeoutException:
        return "Timeout: Page took too long to load", {}
    except WebDriverException as e:
        return f"WebDriver error: {e}", {}
    except Exception as e:
        return f"Error: {e}", {}

def fill_data_in_form(labels_dict, data_dict):
    try:
        for label, web_element in labels_dict.items():
            if label in data_dict:
                value_to_fill = data_dict[label]
                time.sleep(2)
                try:
                    if web_element.tag_name == 'select':
                        select = Select(web_element)
                        options = select.options[1:]
                        if options:
                            random_option = random.choice(options)
                            select.select_by_visible_text(random_option.text)
                            print(f"Selected '{random_option.text}' for '{label}' dropdown.")
                        else:
                            print(f"No valid options found for dropdown '{label}'.")

                    elif web_element.tag_name in ['input', 'textarea']:
                        web_element.clear()
                        web_element.send_keys(value_to_fill)
                        print(f"Filled '{label}' with value: {value_to_fill}")
                    else:
                        print(f"Element type '{web_element.tag_name}' not handled for label '{label}'.")
                
                except (NoSuchElementException, TimeoutException, WebDriverException, Exception) as e:
                    print(f"Error while filling data for '{label}': {e}. Skipping this field.")

            else:
                print(f"No data found for label: {label}. Skipping this field.")

    except Exception as e:
        print(f"Unexpected error while filling data: {e}")

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url")
        labels, labels_dict = extract_labels(url)

        if isinstance(labels, str):
            return render_template("index.html", error=labels)
        else:
            formatted_labels = []
            for form_num, form_labels in labels:
                if "No labels found" not in form_labels:
                    formatted_labels.extend(form_labels)

            prompt = (
                f"Generate a dictionary with the following elements as keys that are passed in the given list: {formatted_labels}. "
                "Ensure each key has a realistic and appropriate value, if any label contains date then date should be in dd-mm-yyyy format. "
                "Generate the unique data everytime.Avoid generating repetitive data and using nested dictionaries. The final result should be a valid JSON object with no ' character, extra code blocks, or explanations."
            )
            try:
                response = requests.post("http://127.0.0.1:5001/generate1", data={"data": prompt})
                if response.status_code == 200:
                    generated_data = response.json().get('output', '{}')
                    
                    start_index = generated_data.find('{')
                    end_index = generated_data.rfind('}')
                    if start_index != -1 and end_index != -1:
                        result = generated_data[start_index:end_index + 1]
                        data_dict = json.loads(result)
                    else:
                        print("No braces found in the generated data.")
                        data_dict = {}

                    fill_data_in_form(labels_dict, data_dict)

                else:
                    generated_data = f"Error: {response.json().get('error')}"
            except Exception as e:
                generated_data = f"Error generating data: {e}"

            return render_template("index.html", labels=labels, generated_data=data_dict)
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
