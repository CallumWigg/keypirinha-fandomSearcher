# Keypirinha Plugin: FandomWiki

This plugin for the [Keypirinha](http://keypirinha.com) launcher allows you to quickly search and access pages on Fandom wikis.

## Download

[https://github.com/CallumWigg/keypirinha-fandomSearcher/releases](https://github.com/CallumWigg/keypirinha-fandomSearcher/releases)

## Install

### Plugin

Download the `Fandom.keypirinha-package` above, and move it to the `InstalledPackage` folder located at:
* `Keypirinha\portable\Profile\InstalledPackages` in **Portable mode**
* **Or** `%APPDATA%\Keypirinha\InstalledPackages` in **Installed mode** (the
  final path would look like
  `C:\Users\%USERNAME%\AppData\Roaming\Keypirinha\InstalledPackages`)

This can quickly be done by typing `keypirinha dir` in  keypirinha to open `\Keypirinha`, then open the `InstalledPackage` folder.

### Settings

Launch Keypirinha, and type `Configure Fandom` to open the config file. Adjust the settings below.

## Options

* [main]
	* `global_results` — pages shown in global catalogue without needing to query `FandomWiki: Text Search` to search page names.
	* `show_wiki_name` — show the name of the wiki which the page belongs to.
  * `show_wiki_name` — the wikis you want to search. place these in the format of `wikis = wiki1,wiki2` where wiki1 will be go to https://wiki1.fandom.com/wiki/ for example.

## Usage

Following commands are created:
* `FandomWiki: Text search` searches for content in pages.
* `FandomWiki: Reload pages` catalog of pages does not refresh automatically as it can take quite some time, making this package unusable in the process. Therefore running this command is needed to index new pages and reindex changes (renamed pages, etc.) in the workspace.

## Todo
Ideally, the script would show the page thumbnails as icons, however keypirinha doesn't have Pillow installed, and I couldn't get it installed within the locked up python it uses. I downloaded the images seperately with a different script and redirected this plugin to find the files, but found it exorbitantly slow as the script looked through all them pages to collect images. Maybe someone smarter could solve this problem, but it's not going to be me. 

## License

This package is distributed under the terms of the MIT license.

### Credits

Portions of the code were inspired by [keypirinha-notionSearcher](https://github.com/wolloda/keypirinha-notionSearcher).