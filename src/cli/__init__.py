from email.policy import HTTP
import typer
import fairly
import pprint

# test for remote operations
def test_connection(repository, **kwargs) -> bool:
    '''Test the connection by listing an accounts datasets in a target repository'''
    # test connection in difference cases
    def test(client):
        try:
            # TODO: this should be a simpler method just a ping method
            client.get_account_datasets()

        except:
            print (f"Could not connect to this repository, check your connection and api token settings")
            raise

        return True

    if 'by_id' in kwargs and kwargs['by_id'] is True: 
    # when providing explicit token (this is mostly for testing)
        if "token" in kwargs:
            c = fairly.client(id=repository, token=kwargs["token"])
            return test(c)
        else:
            c = fairly.client(id=repository)
            return test(c)
    else:
        c = repository
        return test(c)
