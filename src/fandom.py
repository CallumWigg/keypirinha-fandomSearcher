import os
import json
import time
import urllib.request


import keypirinha as kp
import keypirinha_util as kpu
import keypirinha_net as kpnet

class FandomWiki(kp.Plugin):
    ITEMCAT_RESULT = kp.ItemCategory.USER_BASE + 1
    ITEMCAT_RELOAD = kp.ItemCategory.USER_BASE + 2
    ITEMCAT_SEARCH = kp.ItemCategory.USER_BASE + 3

    ACTION_OPEN_BROWSER = "open_browser"
    ACTION_COPY_URL = "copy_url"

    DEFAULT_ICON = "res://Fandom/img/fandom_logo.png"
    ICONS_FOLDER_NAME = "icons"

    def __init__(self):
        super().__init__()
        self.dbg("FandomWiki plugin initialized")
        self._debug = True  # Set this to True to enable detailed debug logging
        self._wiki_pages = []
        self._wikis = []
        self._IMAGES_PATH = os.path.join(self.get_package_cache_path(), self.ICONS_FOLDER_NAME)
        self.logger = getattr(self, "info", print)

    def on_start(self):
        self.dbg("on_start method called")
        self._read_config()
        self.dbg(f"Configuration read. Search mode: {self._SEARCH_MODE}, Show wiki name: {self._SHOW_WIKI_NAME}, Download icons: {self._DOWNLOAD_ICONS}")
        self.dbg(f"Configured wikis: {self._wikis}")
        if self._DOWNLOAD_ICONS:
            os.makedirs(self._IMAGES_PATH, exist_ok=True)
        self._load_wikis()
        self.dbg("Wikis loaded")
        self._refresh_pages()
        self.dbg("Pages refreshed")
        self.set_default_icon(self.load_icon(self.DEFAULT_ICON))
        self.dbg("Default icon set")

    def on_catalog(self):
        catalog = []

        if self._SEARCH_MODE:
            catalog.extend(self._generate_suggestions())
        else:
            catalog.append(self.create_item(
                category=self.ITEMCAT_RESULT,
                label="FandomWiki: Search pages",
                short_desc="Search pages across all configured wikis",
                target="search_pages",
                args_hint=kp.ItemArgsHint.REQUIRED,
                hit_hint=kp.ItemHitHint.KEEPALL
            ))

        catalog.append(self.create_item(
            category=self.ITEMCAT_RELOAD,
            label="FandomWiki: Reload pages",
            short_desc="Reload list of pages from all wikis",
            target="reload_pages",
            args_hint=kp.ItemArgsHint.FORBIDDEN,
            hit_hint=kp.ItemHitHint.NOARGS
        ))

        catalog.append(self.create_item(
            category=self.ITEMCAT_SEARCH,
            label="FandomWiki: Text search",
            short_desc="Search for content across wikis",
            target="text_search",
            args_hint=kp.ItemArgsHint.REQUIRED,
            hit_hint=kp.ItemHitHint.NOARGS
        ))

        self.set_catalog(catalog)

    def on_suggest(self, user_input, items_chain):
        if not items_chain:
            return

        if items_chain[0].category() == self.ITEMCAT_SEARCH:
            self._suggest_text_search(user_input)
        elif items_chain[0].category() == self.ITEMCAT_RESULT or self._SEARCH_MODE:
            self._suggest_pages(user_input)

    def on_execute(self, item, action):
        self.dbg(f"on_execute called for item: {item.label()}")
        if item.category() == self.ITEMCAT_RELOAD:
            self._refresh_pages()
            return

        if item.category() not in (self.ITEMCAT_RESULT, self.ITEMCAT_SEARCH):
            return

        if not action or action.name() == self.ACTION_OPEN_BROWSER:
            kpu.web_browser_command(url=item.target(), execute=True)
        elif action.name() == self.ACTION_COPY_URL:
            kpu.set_clipboard(item.target())

    def on_events(self, flags):
        self.dbg(f"on_events called with flags: {flags}")
        if flags & kp.Events.PACKCONFIG:
            self._read_config()
            self._load_wikis()
            self._refresh_pages()

    def _read_config(self):
        self.dbg("Reading configuration")
        settings = self.load_settings()
        self._SEARCH_MODE = settings.get_bool("global_results", "main", False)
        self._SHOW_WIKI_NAME = settings.get_bool("show_wiki_name", "main", True)
        self._DOWNLOAD_ICONS = settings.get_bool("download_icons", "main", True)
        self._wikis = settings.get("wikis", "main", "").split(',')
        self._wikis = [wiki.strip() for wiki in self._wikis if wiki.strip()]
        self.dbg(f"Configuration read: Search mode: {self._SEARCH_MODE}, Show wiki name: {self._SHOW_WIKI_NAME}, Download icons: {self._DOWNLOAD_ICONS}")
        self.dbg(f"Configured wikis: {self._wikis}")

    def _load_wikis(self):
        self.dbg("Loading wikis")
        self._wikis = [{'name': wiki, 'url': f'https://{wiki}.fandom.com'} for wiki in self._wikis]
        self.dbg(f"Wikis loaded: {self._wikis}")

    def _refresh_pages(self):
        self.dbg("Refreshing pages")
        self._wiki_pages = self._load_cached_pages() or []
        if not self._wiki_pages:
            self.dbg("No cached pages found, fetching from wikis")
            for wiki in self._wikis:
                self.dbg(f"Fetching pages for wiki: {wiki['name']}")
                start_time = time.time()
                pages = self._get_all_pages(wiki)
                self._wiki_pages.extend(pages)
                self.dbg(f"Fetched {len(pages)} pages for {wiki['name']} in {time.time() - start_time:.2f} seconds")
            self._save_cached_pages()
            self.dbg("Pages saved to cache")

        if self._DOWNLOAD_ICONS:
            self.dbg("Downloading icons")
            self._download_icons()
        
        self.dbg(f"Total pages loaded: {len(self._wiki_pages)}")
        self.info("All pages downloaded and ready to use.")

    def _get_all_pages(self, wiki):
        self.dbg(f"Fetching all pages for wiki: {wiki['name']}")
        url = f"{wiki['url']}/api.php"

        all_pages = []
        continue_token = None

        while True:
            params = {
                'action': 'query',
                'list': 'allpages',
                'aplimit': 'max',
                'format': 'json'
            }
            if continue_token:
                params['apcontinue'] = continue_token

            try:
                req = urllib.request.Request(url, data=urllib.parse.urlencode(params).encode())
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read())

                for page in data['query']['allpages']:
                    page_info = self._get_page_info(wiki, page['pageid'])
                    all_pages.append({
                        'pageid': page['pageid'],
                        'title': page['title'],
                        'url': f"{wiki['url']}/wiki/{page['title'].replace(' ', '_')}",
                        'wiki_name': wiki['name'],
                        'thumbnail': page_info['thumbnail'],
                        'categories': page_info['categories']
                    })

                if 'continue' in data:
                    continue_token = data['continue']['apcontinue']
                else:
                    break
            except Exception as e:
                self.err(f"Error fetching pages from {wiki['name']}: {str(e)}")
                break

        return all_pages

    def _get_page_info(self, wiki, pageid):
        url = f"{wiki['url']}/api.php"
        params = {
            'action': 'query',
            'pageids': pageid,
            'prop': 'pageimages|categories',
            'pithumbsize': 500,
            'format': 'json'
        }

        try:
            req = urllib.request.Request(url, data=urllib.parse.urlencode(params).encode())
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read())

            page_data = data['query']['pages'][str(pageid)]
            thumbnail_url = page_data.get('thumbnail', {}).get('source')
            categories = [cat['title'].split(':')[-1] for cat in page_data.get('categories', [])]

            return {
                'thumbnail': thumbnail_url,
                'categories': categories
            }
        except Exception as e:
            self.err(f"Error fetching page info for pageid {pageid} from {wiki['name']}: {str(e)}")
            return {'thumbnail': None, 'categories': []}

    def _get_icon_handle(self, page):
        return self.load_icon(self.DEFAULT_ICON)  
        #icon_path = os.path.join(self._IMAGES_PATH, f"{page['wiki_name']}-{page['pageid']}.png") # Include wiki name
        #self.dbg(f"Trying to load icon from: {icon_path}")  
        #if os.path.exists(icon_path):
        #    self.dbg(f"Icon file exists: {icon_path}")  
        #    return self.load_icon(icon_path)  # Load the pre-downloaded image
        #elif os.path.exists(os.path.join(self._IMAGES_PATH, f"{page['wiki_name']}_logo.png")):
        #    return self.load_icon(os.path.join(self._IMAGES_PATH, f"{page['wiki_name']}_logo.png"))
        #else:
        #    return self.load_icon(self.DEFAULT_ICON) 

    def _generate_suggestions(self):
        suggestions = []
        for page in self._wiki_pages:
            suggestions.append(self.create_item(
                category=self.ITEMCAT_RESULT,
                label=page['title'],
                short_desc=f"[{page['wiki_name']}] {', '.join(page['categories'])}",
                target=page['url'],
                args_hint=kp.ItemArgsHint.FORBIDDEN,
                hit_hint=kp.ItemHitHint.NOARGS,
                icon_handle=self._get_icon_handle(page)
            ))
        return suggestions

    def _suggest_pages(self, user_input):
        suggestions = []
        user_input = user_input.lower()

        for page in self._wiki_pages:
            if (user_input in page['title'].lower() or
                any(user_input in cat.lower() for cat in page['categories']) or
                user_input in page['wiki_name'].lower()):
                
                suggestions.append(self.create_item(
                    category=self.ITEMCAT_RESULT,
                    label=page['title'],
                    short_desc=f"[{page['wiki_name']}] {', '.join(page['categories'])}",
                    target=page['url'],
                    args_hint=kp.ItemArgsHint.FORBIDDEN,
                    hit_hint=kp.ItemHitHint.NOARGS,
                    icon_handle=self._get_icon_handle(page)
                ))

        self.set_suggestions(suggestions, kp.Match.ANY, kp.Sort.NONE)

    def _suggest_text_search(self, user_input):
        parts = user_input.split(' ', 1)
        if len(parts) < 2:
            return

        wiki_name, search_term = parts
        wiki = next((w for w in self._wikis if wiki_name.lower() in w['name'].lower()), None)

        if not wiki:
            self.set_suggestions([self.create_error_item(
                label="Invalid wiki",
                short_desc="Please enter a valid wiki name followed by your search term"
            )])
            return

        url = f"{wiki['url']}/api.php"
        params = {
            'action': 'query',
            'list': 'search',
            'srsearch': search_term,
            'format': 'json'
        }

        try:
            req = urllib.request.Request(url, data=urllib.parse.urlencode(params).encode())
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read())
            search_results = data['query']['search']

            suggestions = []
            for result in search_results:
                suggestions.append(self.create_item(
                    category=self.ITEMCAT_RESULT,
                    label=result['title'],
                    short_desc=f"[{wiki['name']}] {result['snippet']}",
                    target=f"{wiki['url']}/wiki/{result['title'].replace(' ', '_')}",
                    args_hint=kp.ItemArgsHint.FORBIDDEN,
                    hit_hint=kp.ItemHitHint.NOARGS,
                    icon_handle=self._get_icon_handle({'wiki_name': wiki['name'], 'pageid': result['pageid']})
                ))

            self.set_suggestions(suggestions)
        except Exception as e:
            self.err(f"Error performing text search on {wiki['name']}: {str(e)}")
            self.set_suggestions([self.create_error_item(
                label="Search error",
                short_desc=f"An error occurred while searching {wiki['name']}: {str(e)}"
            )])

    def _create_error_item(self, label, short_desc):
        return self.create_item(
            category=kp.ItemCategory.ERROR,
            label=label,
            short_desc=short_desc,
            target=label,
            args_hint=kp.ItemArgsHint.FORBIDDEN,
            hit_hint=kp.ItemHitHint.NOARGS
        )

    def _clean_snippet(self, snippet):
        # Remove HTML tags from the snippet
        clean_text = re.sub('<[^<]+?>', '', snippet)
        # Replace multiple spaces with a single space
        clean_text = re.sub('\s+', ' ', clean_text).strip()
        return clean_text

    def on_activated(self):
        pass

    def on_deactivated(self):
        pass

    def on_events(self, flags):
        if flags & kp.Events.PACKCONFIG:
            self._read_config()
            self._load_wikis()
            self._refresh_pages()

    def _create_actions(self):
        actions = [
            self.create_action(
                name=self.ACTION_OPEN_BROWSER,
                label="Open in browser",
                short_desc="Open the page in your default web browser"
            ),
            self.create_action(
                name=self.ACTION_COPY_URL,
                label="Copy URL",
                short_desc="Copy the page URL to the clipboard"
            )
        ]
        self.set_actions(self.ITEMCAT_RESULT, actions)

    def _should_terminate(self):
        if self.should_terminate():
            self.set_suggestions([self.create_error_item(
                label="Interrupted",
                short_desc="The search operation was interrupted"
            )])
            return True
        return False

    def on_events(self, flags):
        if flags & kp.Events.PACKCONFIG:
            self._read_config()
            self._load_wikis()
            self._refresh_pages()
        elif flags & kp.Events.NETOPTIONS:
            self._refresh_pages()

    def on_executed(self, item):
        if item and item.category() == self.ITEMCAT_RELOAD:
            self._refresh_pages()
            self.set_suggestions([self.create_item(
                category=kp.ItemCategory.NOTIFICATION,
                label="Pages reloaded",
                short_desc="The list of pages has been refreshed",
                target="pages_reloaded",
                args_hint=kp.ItemArgsHint.FORBIDDEN,
                hit_hint=kp.ItemHitHint.IGNORE
            )])

    def _load_cached_pages(self):
        cache_path = os.path.join(self.get_package_cache_path(), "pages_cache.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r') as cache_file:
                    return json.load(cache_file)
            except Exception as e:
                self.err(f"Error loading cached pages: {str(e)}")
        return None

    def _save_cached_pages(self):
        cache_path = os.path.join(self.get_package_cache_path(), "pages_cache.json")
        try:
            with open(cache_path, 'w') as cache_file:
                json.dump(self._wiki_pages, cache_file)
        except Exception as e:
            self.err(f"Error saving cached pages: {str(e)}")

    def _refresh_pages(self):
        self._wiki_pages = self._load_cached_pages() or []
        if not self._wiki_pages:
            for wiki in self._wikis:
                self._wiki_pages.extend(self._get_all_pages(wiki))
            self._save_cached_pages()

    def _get_wiki_info(self, wiki):
        url = f"{wiki['url']}/api.php"
        params = {
            'action': 'query',
            'meta': 'siteinfo',
            'siprop': 'general',
            'format': 'json'
        }

        try:
            req = urllib.request.Request(url, data=urllib.parse.urlencode(params).encode())
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read())
            return data['query']['general']
        except Exception as e:
            self.err(f"Error fetching wiki info for {wiki['name']}: {str(e)}")
            return None

    def on_suggest(self, user_input, items_chain):
        self.dbg(f"on_suggest called with input: {user_input}")
        if items_chain and items_chain[-1].category() == self.ITEMCAT_SEARCH:
            self._suggest_text_search(user_input)
        elif self._SEARCH_MODE or (items_chain and items_chain[-1].category() == self.ITEMCAT_RESULT):
            self._suggest_pages(user_input)



    def on_activated(self):
        self._create_actions()

if __name__ == "__main__":
    FandomWiki()