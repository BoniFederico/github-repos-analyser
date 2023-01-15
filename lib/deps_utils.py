import json,os,shutil
from lib.system_utils import exc,diff
from packageurl import PackageURL
from pathlib import Path


def js_parsed_deps(folder:str):
    if not(os.path.isfile(os.path.join(folder,'package.json'))):
                  with open('package.json', 'w') as f:
                    json.dump(dict(), f, indent=2)

    res=exc(f'npx check-imports ',shell=True)
    packages = list()
    for package in res.split('dependencies to add')[1:]:
        for line in package.splitlines():
            if line.startswith("-"):
                pckg=line[2:].replace('^','').replace('>','').replace('~','').replace('@','',max(line[2:].count('@')-1,0))
                try:
                    packages.append({
                        'purl':'pkg:npm/'+pckg,
                        'name':pckg.split('@')[0].split('/')[len(pckg.split('@')[0].split("/"))-1],
                        'package_manager':'npm',
                        'version':pckg.split('@')[1],
                        'namespace':''.join(pckg.split('@')[0].split('/')[:len(pckg.split('@')[0].split("/"))-1]).replace('%','').replace('@','')
                    })
                except Exception as e:
                    pass
                if  len(line)>0 and line[0].isdigit():
                    break   
    return packages     

def get_deps_from_sbom(path:str,repo:str):
    if not(path.endswith('sbom.json')):
        return
    with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    packages = list()
    for package in [p for p in data['packages'] if 'name' in p and p['name']!=repo]:
        if 'externalRefs' not in package:
            continue
        purl=[extRef['referenceLocator'] for extRef in package['externalRefs'] if 'referenceType' in extRef and extRef['referenceType'] == 'purl'].pop().replace('%40','@') #%40 due to sbom-tool bug
        purl_str=PackageURL.from_string(purl).to_string()
        purl = PackageURL.from_string(purl).to_dict()
        packages.append({
            'purl':purl_str.replace('%40',''),
            'name':purl['name'],
            'package_manager':purl['type'],
            'version':purl['version'],
            'namespace':purl['namespace'].replace('@','') if 'namespace' in purl and purl['namespace'] is not None else ''})
    return packages

def py_parsed_deps(org_folder:str,org:str,repo:str,already_present_deps:dict=None):
    repo_folder = os.path.join(org_folder,repo)
    Path(os.path.join(repo_folder,"parsed_dependencies")).mkdir(parents=True, exist_ok=True)
    req_path=os.path.join(repo_folder,'parsed_dependencies','requirements.txt')
    try:
        res=exc(f'python -m pipreqsnb.pipreqsnb  {repo_folder} --savepath {req_path}')
    except Exception as e1:
        try:
            res=exc(f'python -m lib2to3 -w {repo_folder}')
            res=exc(f'python -m pipreqsnb.pipreqsnb  {repo_folder} --savepath {req_path}')
        except Exception as e2:
            print('Error')
    res=exc(""".\sbom-tool\sbom-tool.exe generate -b {0}
                                         -bc {0} 
                                         -pn {1} 
                                         -pv 1.0 
                                         -ps {2} 
                                         -nsb https://github.com/{2} 
                                         -m {3}""".format(os.path.join(repo_folder),
                                                          repo,
                                                          org,
                                                          repo_folder).replace('\n',''))
    shutil.move(os.path.join(repo_folder,'_manifest','spdx_2.2','manifest.spdx.json'), os.path.join(org_folder,'par_{}_{}_sbom.json'.format(org,repo)))
    shutil.rmtree(os.path.join(repo_folder,'_manifest'), ignore_errors=True, onerror=None)

    parsed = get_deps_from_sbom(os.path.join(org_folder,'par_{}_{}_sbom.json'.format(org,repo)),repo)
    return parsed if already_present_deps is None else [par for par in parsed if par['purl'] in diff([p['purl'] for p in parsed],[p['purl'] for p in already_present_deps])]

 