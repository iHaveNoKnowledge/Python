import urllib.request
import json
import zipfile
import os
import shutil

def download_chromedriver():
    try:
        url = 'https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json'
        print(f"Fetching data from {url}...")
        response = urllib.request.urlopen(url)
        data = json.loads(response.read())

        target_version_prefix = '146.0.7680.'
        download_url = None
        exact_version = None

        for version_info in data.get('versions', []):
            if version_info.get('version', '').startswith(target_version_prefix):
                for download in version_info.get('downloads', {}).get('chromedriver', []):
                    if download.get('platform') == 'win64':
                        download_url = download.get('url')
                        exact_version = version_info.get('version')
                        break
                if download_url:
                     break
        
        if not download_url:
            print(f"Could not find download URL for version {target_version_prefix}")
            return False

        print(f"Found version: {exact_version}")
        print(f"Downloading from {download_url}...")
        
        zip_path = 'chromedriver.zip'
        urllib.request.urlretrieve(download_url, zip_path)

        print('Extracting...')
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall('temp_chromedriver')

        source_file = 'temp_chromedriver/chromedriver-win64/chromedriver.exe'
        target_file = r'C:\bin\chromedriver.exe'

        print(f"Killing existing chromedriver processes...")
        os.system('taskkill /f /im chromedriver.exe >nul 2>&1')

        print(f"Copying to {target_file}...")
        if os.path.exists(target_file):
            print(f"Removing old {target_file}...")
            os.remove(target_file)
        
        shutil.copy2(source_file, target_file)
        print("Successfully updated chromedriver!")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Cleaning up temporary files...")
        try:
            if os.path.exists('chromedriver.zip'):
                os.remove('chromedriver.zip')
            if os.path.exists('temp_chromedriver'):
                shutil.rmtree('temp_chromedriver')
        except:
            pass

if __name__ == "__main__":
    download_chromedriver()
