import requests, logging
import os
import zipfile
import shutil
from pathlib import Path


class GitHubApi(object):

    def __init__(self, access_token:str):
        self.headers={'Authorization': 'token %s' % access_token,"Accept": "application/vnd.github+json"}

    def req(self,url:str):
        response=requests.get(url,headers=self.headers)
        response=response.json()
        if 'message' in response:
            if response['message']=='Not Found':
                raise Exception('Not Found')
            elif response['message']=='Bad credentials':
                raise Exception('Bad Credentials (Not valid personal access token)')
        return response

def download_repo(user:str,repo:str,folder:str,branch=None):
    Path(folder).mkdir(parents=True, exist_ok=True)
    _download_repo(get_zip_link(user, repo, branch="master" if branch is None else branch), folder,log=False)
    return os.path.join(os.getcwd(),folder)

logging.getLogger('requests').setLevel(logging.CRITICAL)
#https://gist.github.com/megat69/173594870a63a4374605b5fb98ce7426
def _download_repo(URL:str, folder:str, files_to_delete:(list)=(".gitattributes", "README.md"), log:bool=False, notify_function=print, *args, **kwargs):
    

	"""
	Downloads the specified repository into the specified folder.
	:param URL: The URL of the repository main archive.
	:param folder: The folder to place the repository in.
	:param files_to_delete: The files to delete after downloading the repository. DEFAULT : '.gitattributes', 'README.md'
	:param log: Log the informations in the console. DEFAULT : True
	:param notify_function: The function that will get the log as argument. DEFAULT : print()
	"""
	logging.getLogger('requests').setLevel(logging.CRITICAL)
	if log: notify_function("Downloading... This might take a while.", *args, **kwargs)
	r = requests.get(URL)
	assert r.status_code == 200, "Something happened.\nStatus code : " + str(r.status_code)

	if log: notify_function("Writing the zip...", *args, **kwargs)
	# Writing the zip
	with open(f"{folder}.zip", "wb") as code:
		code.write(r.content)
		code.close()

	# Creating a folder for the zip content
	if not os.path.exists(folder):
		os.mkdir(folder)

	if log: notify_function("Extracting...", *args, **kwargs)
	# Extracting the zip
	with zipfile.ZipFile(f"{folder}.zip", "r") as zip_ref:
		zip_ref.extractall(folder)

	if log: notify_function("Moving the files...", *args, **kwargs)
	suffix = URL.split("/")[-1].replace(".zip", "", 1)
	repo_name = URL.split("/")[4]
	# Moving the file to parent
	for filename in os.listdir(os.path.join(folder, f'{repo_name}-{suffix}')):
		shutil.move(os.path.join(folder, f'{repo_name}-{suffix}', filename), os.path.join(folder, filename))
	# Deleting unnecessary files
	shutil.rmtree(f"{folder}/{repo_name}-{suffix}")
	os.remove(f"{folder}.zip")
	for file in files_to_delete:
		try:
			os.remove(f"{folder}/{file}")
		except FileNotFoundError:
			pass

	if log: notify_function("Download complete !", *args, **kwargs)

def get_zip_link(username:str, repository:str, branch:str="main"):
	return f"https://github.com/{username}/{repository}/archive/refs/heads/{branch}.zip"



def get_contributors(org:str,repo:str,github_api:object):
    res_per_page,starting_page= 50,1
    counter=0
    results = github_api.req(f'https://api.github.com/repos/{org}/{repo}/contributors?page={starting_page}&per_page={res_per_page}')
    contributors=list()
    while len(results)>0:
        contributors.extend(results)
        starting_page+=1
        results = github_api.req(f'https://api.github.com/repos/{org}/{repo}/contributors?page={starting_page}&per_page={res_per_page}')

        counter+=1
        if (counter>20):
            break
    return contributors

def get_commits(org:str,repo:str,github_api:object):
    res_per_page,starting_page= 50,1
    counter=0
    results = github_api.req(f'https://api.github.com/repos/{org}/{repo}/commits?page={starting_page}&per_page={res_per_page}')
    commits=list()

    while len(results)>0:
        commits.extend(results)
        starting_page+=1
        results = github_api.req(f'https://api.github.com/repos/{org}/{repo}/commits?page={starting_page}&per_page={res_per_page}')

        counter+=1
        if (counter>20):
            break
    return commits

def get_pullrequests(org:str,repo:str,github_api:object):
    res_per_page,starting_page= 50,1
    counter=0
    results = github_api.req(f'https://api.github.com/repos/{org}/{repo}/pulls?state=all&page={starting_page}&per_page={res_per_page}')
    pullreqs=list()

    while len(results)>0:
        pullreqs.extend(results)
        starting_page+=1
        results = github_api.req(f'https://api.github.com/repos/{org}/{repo}/pulls?state=all&page={starting_page}&per_page={res_per_page}')

        counter+=1
        if (counter>20):
            break
    return pullreqs