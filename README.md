<!--
Avoid using this README file for information that is maintained or published elsewhere, e.g.:

* charmcraft.yaml > published on Charmhub
* documentation > published on (or linked to from) Charmhub
* detailed contribution guide > documentation or CONTRIBUTING.md

Use links instead.
-->

# phased-updater-operator

Charmhub package name: phased-updater-operator
More information: https://charmhub.io/phased-updater-operator

Describe your charm in one or two sentences.

## Other resources

<!-- If your charm is documented somewhere else other than Charmhub, provide a link separately. -->

- [Read more](https://example.com)

- [Contributing](CONTRIBUTING.md) <!-- or link to other contribution documentation -->

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


