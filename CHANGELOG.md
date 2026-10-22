# Changelog

## [0.3.0](https://github.com/vertracloud/sdk-api-py/compare/v0.2.2...v0.3.0) (2026-10-22)


### ⚠ BREAKING CHANGES

* plan names and multiple custom domains per app

### Features

* plan names and multiple custom domains per app ([1df9eab](https://github.com/vertracloud/sdk-api-py/commit/1df9eab6d548a6136409652419afd26dbd6c8b41))


### Bug Fixes

* drop the Authorization header when a redirect changes scheme, host or port ([70f5451](https://github.com/vertracloud/sdk-api-py/commit/70f5451d8ee02579344ac2fde46a16ed1b9952eb))
* reject empty and dot path segments before sending a request ([2964db9](https://github.com/vertracloud/sdk-api-py/commit/2964db9c6da64ce0427ee4b4c2975b012edbad8e))
* **upload:** escape quotes and reject CR/LF in multipart Content-Disposition ([e56ebb0](https://github.com/vertracloud/sdk-api-py/commit/e56ebb0ef9717cd45d766d94905225ede8c4466e))

## [0.2.2](https://github.com/vertracloud/sdk-api-py/compare/v0.2.1...v0.2.2) (2026-10-18)


### Bug Fixes

* support async app creation (building status, wait_until_ready) ([044a73f](https://github.com/vertracloud/sdk-api-py/commit/044a73f981f540e1e070d52c0243469448243e46))

## [0.2.1](https://github.com/vertracloud/sdk-api-py/compare/v0.2.0...v0.2.1) (2026-10-15)


### Features

* **blob:** add rename_on_conflict to put and copy ([6773c4c](https://github.com/vertracloud/sdk-api-py/commit/6773c4cfa63032875dfe1b3f92967fe3128b4e7c))

## [0.2.0](https://github.com/vertracloud/sdk-api-py/compare/v0.1.5...v0.2.0) (2026-10-15)


### Features

* add Blob Storage resource ([77cb94d](https://github.com/vertracloud/sdk-api-py/commit/77cb94d692612fb8a663330208738c89f402a4c7))
* add expires_at to Pix payment and order status ([fa087b8](https://github.com/vertracloud/sdk-api-py/commit/fa087b887b17c4f188713e3c8002ad5065fc81fa))
* web_content on blob custom domains ([6cc7d84](https://github.com/vertracloud/sdk-api-py/commit/6cc7d84538ab666737bafe9b697f5db0410a95c7))

## [0.1.5](https://github.com/vertracloud/sdk-api-py/compare/v0.1.4...v0.1.5) (2026-10-12)


### Features

* **apps:** releases, rollback, deploy settings and upload message ([496c984](https://github.com/vertracloud/sdk-api-py/commit/496c984fa45352c58bd6dbff52a41cbd87a334b4))
* **types:** add first_started_at to APIApplicationRelease ([71fbdb9](https://github.com/vertracloud/sdk-api-py/commit/71fbdb9a5d90bfc31a86239419013b9301f819a5))

## [0.1.4](https://github.com/vertracloud/sdk-api-py/compare/v0.1.3...v0.1.4) (2026-10-10)


* release 0.1.4 ([b8a1182](https://github.com/vertracloud/sdk-api-py/commit/b8a1182904949ea6676b6dca7da4e25a5aaa4a35))


### Features

* **apps:** add destination path option to file upload ([e19372d](https://github.com/vertracloud/sdk-api-py/commit/e19372d3302481fa5e509d3e9f0f0c040c6731d3))

## [0.1.3](https://github.com/vertracloud/sdk-api-py/compare/v0.1.2...v0.1.3) (2026-10-05)


* release 0.1.3 ([65123be](https://github.com/vertracloud/sdk-api-py/commit/65123bec19e4cf26303e71706bfbc6bc678669ce))


### Features

* **billing:** billing details, card provider and new order fields ([f3191a5](https://github.com/vertracloud/sdk-api-py/commit/f3191a5b6666a007f92b0b42b55e13926a502ab7))

## [0.1.2](https://github.com/vertracloud/sdk-api-py/compare/v0.1.1...v0.1.2) (2026-09-30)


### ⚠ BREAKING CHANGES

* remove autorestart/auto_restart field from the application contract

* release 0.1.2 ([8e9ff23](https://github.com/vertracloud/sdk-api-py/commit/8e9ff23fe22ea9fe6416d2f4259751ed8cf2584f))


### Features

* remove autorestart/auto_restart field from the application contract ([07ec328](https://github.com/vertracloud/sdk-api-py/commit/07ec32865b341e7fafd02926fb7192b91a858dd4))

## [0.1.1](https://github.com/vertracloud/sdk-api-py/compare/v0.1.0...v0.1.1) (2026-09-23)


### Bug Fixes

* drop resource-organization segment from folder and favorite routes ([2836fec](https://github.com/vertracloud/sdk-api-py/commit/2836fec743039789f2bdbc62f80db4b9cae23563))

## 0.1.0 (2026-09-23)


### Features

* add apps, databases, snapshots, account, workspaces and billing resources ([9c67589](https://github.com/vertracloud/sdk-api-py/commit/9c6758937e20b4fadb4f413cadba2884868b6e14))
* add HTTP transport and error types ([0ff9ac5](https://github.com/vertracloud/sdk-api-py/commit/0ff9ac5ef13235ab10d83d5e869235ec1f73bd36))
* add SSE realtime log streaming ([753cd7f](https://github.com/vertracloud/sdk-api-py/commit/753cd7f0433539eb5f291a7f5b582ac1dc0c043a))

## Changelog
