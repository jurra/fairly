import typer
import fairly
import pprint
'''
fairly create [path]

# this should write or save to fairly.json
fairly repository list
fairly repository add --id <id> --name <name> --api-url <url> --token <token>
fairly repository update <id> --token <token>
fairly repository remove <id>

'''

pp = pprint.PrettyPrinter(indent=4)

app = typer.Typer()

@app.command()
def list():
    '''List all repositories supported by fairly'''
    repositories = fairly.get_repositories()
    for key in repositories:
        print(key)

@app.command()
def add(
    id: str = typer.Option("", help="Repository ID"),
):
    ''' Add a repository to the config file,
    Notice that this should only be allowed once there is a corresponing module
    for the repository.
    '''
    if id:
        print(f"Adding repository {id}")
        fairly.add_repository(id)

@app.command()
def show(name: str):
    ''' Show a repository details '''
    for key in fairly.get_repositories():
        if key == name:
            pp.pprint(fairly.get_repositories()[key])
            break
        else:
            print(f"Repository {name} not found")
            break

@app.command()
def update(
    id: str,
    token: str = typer.Option("", help="Repository token")
):
    ''' Update a repository token '''
    if token:
        # TODO: This method or something similar doesnt exist yet
        fairly.update_repository(id, token)


if __name__ == "__main__":
    app()

