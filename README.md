# Living Proof Labs common library

Shared Python libraries for Living Proof Labs tools. Apache-2.0. **No CLI or plugin manager.**

**Start here: [documentation](https://docs.livingprooflabs.com/livingproof-common/).**
[Documentation home](https://docs.livingprooflabs.com/) ·
[Source](https://github.com/Living-Proof-Labs/livingproof-common) ·
[Help / report an issue](https://github.com/Living-Proof-Labs/livingproof-common/issues) ·
[License](docs/license.md)

## Consumer usage

Use Python 3.11 or newer. [Install a released wheel and run the identity example](docs/usage.md#install-a-release),
then [add the consumer build hook](docs/usage.md#consumer-contract) to preserve your
own package's identity in wheel and source builds. Debian packages are also
available. This library supplies identity and build provenance; it does not run
robots, manage plugins, or provide a command-line application.

Consumer build and runtime requirements must pin the same tested release.
The development manual's source revision and test-candidate metadata are separate
from published package releases. See the manual's **Version and source** page.

## Develop with the existing environment

Contributors use the existing Docker/Task environment. Start with
[developer setup](docs/development.md#develop-with-the-existing-environment).
The manual generates both host-wrapper and prepared-container Task commands from
the reviewed Taskfiles. [Verification and previews](docs/verification.md) explains
individual test results, bounded scenarios, measured coverage and retained artifacts.

## Packages and release

See [package and release operations](docs/development.md#packages-and-release).
For the selected release's artifacts and notes, use
[GitHub Releases](https://github.com/Living-Proof-Labs/livingproof-common/releases).

## Contribute

Follow [contribution guidance](docs/contributing.md), including the pinned shared
standards and this library's local instructions.
