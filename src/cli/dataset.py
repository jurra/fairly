'''
# Create a local dataset under path with default template
fairly dataset create <path>

# Create a local dataset under path with the specified template
# <template> = 'zeondo, 4tu, default'
fairly dataset create <path> --template <template>

# Show information about the specified local dataset
# show some metadata + handy info about the dataset
fairly dataset show <path>

fairly dataset upload <path> <repository>
# Ex. fairly dataset upload ~/my-dataset zenodo
    
# Upload dataset by using a custom token (can be useful for e.g. data stewards)
fairly dataset upload <path> <repository> --token <token>
fairly upload <path> <repository> --token <token>
# If the dataset was not uploaded before: create remote entry (get id), set metadata, upload all files, upload local manifest to add id
# If the dataset was uploaded (id exists in manifest): update remote metadata, upload added and modified files, delete removed files

metadata:
  4tu_id: <id>

files:

# Download a dataset by using its URL address or DOI
# fairly automatically recognize them and creates corresponding client
fairly dataset download <url|doi>
fairly download <url|doi>
# Ex. fairly download https://zenodo.org/record/6026285

fairly dataset download <url|doi> --token <token> 
fairly dataset download <repository> <id>
fairly dataset download --repository zenodo --id 6026285

# TODO: Assess if this is a good idea or not????
# Update 'title' metadata of the local dataset
fairly dataset update <path> --title <title> 

'''
import os
import shutil
import pprint
import yaml


import typer
import fairly


app = typer.Typer()

# fairly dataset create <path>
@app.command()
def create(
    metadata: str = typer.Argument("", help="Metadata specification to be used for the dataset, for example figshare or zenodo."),
) -> None:
    '''Create a local dataset under path with default template'''
    print(f"Creating dataset with template {metadata}")
    # Should create the template in the current working directory

    # copy file and paste it in the current working directory
    fairly_path = os.path.dirname(fairly.__file__)
    template_path = os.path.join(fairly_path, "data","templates", f'{metadata}.yaml')
    shutil.copy(template_path, os.path.join(os.getcwd(), "manifest.yaml"))

if __name__ == "__main__":
    app()