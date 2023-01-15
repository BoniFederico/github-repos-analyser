# GitHub Repository Analyzer

The project was carried out for the master's thesis in computer engineering at the University of Trieste.

# Requirements

### Python (all notebooks)
The project is written in Python and relies on a set of Python notebooks. It is therefore necessary to install Jupyter and Python (the minimum Python version required is 3.9.0)
### Packages
The third-party packages used are listed in the requirements.txt file and can be installed using the following command in the root folder:
``` bash
pip install -r requirements.txt
```
### Microsoft sbom-tool (notebook_2)
Microsoft's [sbom-tool](https://github.com/microsoft/sbom-tool) software must be present within the *sbom-tool* folder. The software can be downloaded from the page [sbom-tool relases](https://github.com/microsoft/sbom-tool/releases). 
#### Further requirements
In addition, in order to detect all the packages with *sbom-tool*, the following are required (from the [component-detection](https://github.com/microsoft/component-detection/blob/main/docs/feature-overview.md)):

- Conda v4.10.2+ (for Conda dependencies)
- Gradle 7 (for Java dependencies (Gradle))
- Go 1.11+ (for Go dependencies))
- Maven (for Java dependencies (Maven))
- Internet connection (for Python (PyPi) transitive dependencies)

### Grype (notebook_3 (grype_vulns))
The [Grype](https://github.com/anchore/grype) software from Anchore is used. In order to execute Grype on Windows, it is necessary to install WSL (Windows Subsystem for Linux) and an OS. Below the commands used to install WSL (if it doesn't work, enable WSL features from Windows settings: 'Turn Windows features on or off'):
``` bash
! wsl --install -d ubuntu
! wsl --set-default Ubuntu
```
And then install Grype:
``` bash
! wsl curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | wsl sh -s -- -b /usr/local/bin
```

#### Grype database (notebook_3 (java_grype))
In order to collect Java vulnerabilities, it is necessary to connect to the Grype database directly. Grype DB is a sqlite database and it is stored in a temporary folder. It is necessary to insert the database in the *grype_db* folder. It is possible to execute the following command to get the path of the database and copy it in the grype_db project folder:

``` bash
wsl grype db status
```

# Database 
The structure of the database is the following. More information about the tables can be found in the notebook_0 notebook.
![db structure](db_images/structure.png?raw=true "Title")

# Notebook & Database
The figure below briefly shows which notebooks are in charge of doing what. Arrows specify which database tables are filled by which notebooks.
![db structure](db_images/cards.png?raw=true "Title")
