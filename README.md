# phased-updater-operator

Charmhub package name: phased-updater-operator

More information: https://charmhub.io/phased-updater-operator

This charm deploys the phased-updater service. This service controls the reach of Ubuntu Stable Release Updates (SRUs), making updates slowly available to more and more users, until they are phased to 100%. If an update starts generating too many error reports, it is halted and needs to be investigated.

## Other resources

- [Read more about phasing updates](https://documentation.ubuntu.com/project/SRU/explanation/standard-processes/#phasing)

- See the [Juju documentation](https://documentation.ubuntu.com/juju/3.6/howto/manage-charms/) for more information about developing and improving charms.

# Deployment

a) obtain launchpad credentials:
```
$ ppa credentials
Launchpad credentials written to credentials.oauth
```

b) Create juju secret
```
$ juju add-secret launchpadlib_secret credentials#file=credentials.oauth
secret:<somehash>
```
Take note of the result, it will be needed later. If you miss it, just run `juju list-secrets` to find it again.

c) Deploy the application with this config. One way is via the command-line:
```
$ juju deploy phased-updater-operator --config launchpadlib_secret_id=secret:<somehash>
```

d) Grant access to that secret. This can only be done after the application is deployed, i.e., it must exist already:
```
$ juju grant-secret launchpadlib_secret phased-updater-operator
```
