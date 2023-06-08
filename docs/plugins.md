# Plugins
The primary purpose of docleaner is to process documents supplied by users, specifically to analyze and strip all potentially privacy-invasive metadata (other arbitrary use cases are possible). Since the metadata format within documents/files highly depends on its type, code for supported document types is encapsulated and supplied in the form of *plugins*.

Each plugin is supposed to be importable by Python as a package `docleaner.api.plugins.<plugin_name>`. The minimal requirement for a valid plugin is the implementation of a method 
```
get_job_types(config: configparser.ConfigParser) -> List[JobType]`
```
in `docleaner.api.plugins.<plugin_name>.__init__.py`. During initialization, docleaner attempts to import all plugin packages enabled in `docleaner.conf` by calling their respective `get_job_types()` method and passing the current configuration as sole parameter. We recommend to parse at least the plugin config keys `sandbox` (in case multiple types of sandboxes are supported by a plugin) and `containerized.image` to let users select the name and version of the container image to use for processing. The method `get_job_types()` is expected to return a list of `JobType` instances, each of which represents a single document type supported by the plugin.

The included PDF plugin can be used as reference implementation. It returns a single `JobType` defined as follows:
```
JobType(
    id="pdf",
    mimetypes=["application/pdf"],
    readable_types=["PDF"],
    sandbox=ContainerizedSandbox(
        container_image=config.get(section, "containerized.image"),
        podman_uri=config.get("docleaner", "podman_uri"),
    ),
    metadata_processor=process_pdf_metadata,
)
```
The `id` attribute has to be a unique identifier amongst all registered `JobType`s. The list of strings in `mimetypes` specifies all MIME types that should be processed by this `JobType`. Each supplied job/document will initially be passed to a `FileIdentifier`, which in the default implementation returns the document's MIME type (see also [architecture documentation](architecture.md)). The first `JobType` supporting that MIME type will be selected to process the document. The list of strings in `readable_types` is used by the frontend to show supported document types to users. The `sandbox` attribute expects a `Sandbox` instance that is able to process the specified MIME types and `metadata_processor` should point to a metadata post-processing method that is called twice after the sandbox has finished execution: once for the initial (prior to processing) and once for the final (after processing) document metadata. That method is supposed to take raw metadata as returned from the sandbox (as `dict`) and parse it into a new `DocumentMetadata` instance. At this point it's reasonable to strip out metadata that isn't likely to contain privacy-invasive information.

The actual file processing takes places within unprivileged isolated sandboxes. Plugins are expected to use one of the default `Sandbox` implementations or ship their own. By default, a plugin may provide the sources for a container image (such as in `plugins/pdf/sandbox/`) that can be launched with `ContainerizedSandbox` and exhibits the following behaviour:
* the container idles indefinitely after startup (e.g. via `sleep infinity`)
* `/opt/analyze <source_path>` is an executable script or program that analyzes the given document and writes its metadata as JSON to stdout
* `/opt/process <source_path> <result_path>` is an executable script or program that parses the source document, strips its metadata and writes the resulting document to `result_path`.
In case a plugin provides a custom `Sandbox` implementation, keep in mind that its `process()` method should be non-blocking to support processing of multiple documents in parallel, e.g. by properly using asyncio or launching a separate thread or subprocess for each invocation.

To build a sandbox image within the development environment, invoke `build_plugin <Containerfile>`. When building in release mode, all `Containerfile`s found within the `plugins/` directory will be built automatically.

Remember to include tests with each plugin. Unit tests, used primarily to test metadata post-processing, should be placed in `api/tests/unit/plugins/test_<plugin_name>.py`. Integration tests that initialize a `Sandbox` and process sample files reside in `api/tests/integration/plugins/test_<plugin_name>_processing.py`.
