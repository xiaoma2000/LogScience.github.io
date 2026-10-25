#!/usr/bin/env python3
"""Validate LogScience JSON content and optionally six built Jekyll routes.

Uses Python's standard library; never changes content or requests remote URLs.
"""

from __future__ import annotations

import argparse
from datetime import date
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urljoin, urlsplit


CORE_ROUTES = ("/", "/research/", "/team/", "/publications/", "/news/", "/contact/")
DATA_FILES = ("news", "team", "research", "group_publications", "home")
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


class ContentChecker:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.errors = []
        self.counts = {}

    def error(self, where, message):
        self.errors.append(f"{where}: {message}")

    def text(self, record, key, where, optional=False):
        if optional and key not in record:
            return ""
        value = record.get(key)
        if not isinstance(value, str) or not value.strip():
            self.error(where + "." + key, "must be a non-empty string")
            return ""
        return value

    def objects(self, value, where):
        if not isinstance(value, list):
            self.error(where, "must be an array")
            return []
        result = []
        for index, record in enumerate(value):
            location = f"{where}[{index}]"
            if not isinstance(record, dict):
                self.error(location, "must be an object")
            else:
                result.append((record, location))
        return result

    def strings(self, value, where, allow_empty=False):
        if not isinstance(value, list) or (not value and not allow_empty):
            self.error(where, "must be an array of non-empty strings")
            return []
        result = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item.strip():
                self.error(f"{where}[{index}]", "must be a non-empty string")
            else:
                result.append(item)
        return result

    def identifier(self, record, where, seen, kind="id"):
        value = self.text(record, "id", where)
        if value:
            if not ID_PATTERN.fullmatch(value):
                self.error(where + ".id", "use lowercase letters, numbers and hyphens")
            if value in seen:
                self.error(where + ".id", "duplicate " + kind + ": " + value)
            seen.add(value)
        return value

    def year(self, record, key, where, optional=False):
        if optional and key not in record:
            return
        value = record.get(key)
        if type(value) is not int or not 1900 <= value <= 2200:
            self.error(where + "." + key, "must be an integer year between 1900 and 2200")

    def web_url(self, value, where):
        if not isinstance(value, str):
            self.error(where, "must be an absolute HTTP(S) URL")
            return False
        try:
            parsed = urlsplit(value)
            valid = (parsed.scheme in ("https", "http") and bool(parsed.hostname)
                     and not parsed.username and not parsed.password and not re.search(r"\s", value))
            parsed.port  # Also reject malformed port declarations.
        except ValueError:
            valid = False
        if not valid:
            self.error(where, "must be an absolute HTTP(S) URL without credentials or whitespace")
        return valid

    def image(self, record, where, required=False, alt_required=False):
        if required and "image" not in record:
            self.error(where + ".image", "is required")
        for key in ("image", "image_web"):
            if key not in record:
                continue
            value = self.text(record, key, where)
            if not value:
                continue
            try:
                parsed = urlsplit(value)
            except ValueError:
                self.error(where + "." + key, "must be a local image path")
                continue
            if parsed.scheme or parsed.netloc or not value.startswith("/") or "\\" in value:
                self.error(where + "." + key, "must be a local path starting with /")
                continue
            target = (self.root / unquote(parsed.path).lstrip("/")).resolve()
            if not target.is_relative_to(self.root):
                self.error(where + "." + key, "points outside the website root")
            elif not target.is_file():
                self.error(where + "." + key, "missing local image: " + value)
        if alt_required:
            self.text(record, "image_alt", where)
        if "image_fit" in record and record["image_fit"] not in ("cover", "contain"):
            self.error(where + ".image_fit", "must be cover or contain")
        if "image_width" in record or "image_height" in record:
            for key in ("image_width", "image_height"):
                value = record.get(key)
                if type(value) is not int or value <= 0:
                    self.error(where + "." + key, "must be a positive integer; provide both image dimensions")

    def load(self, name, optional=False):
        path = self.root / "_data" / (name + ".json")
        if optional and not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=unique_json_object)
        except (OSError, UnicodeError, ValueError) as exc:
            self.error("_data/" + name + ".json", str(exc))
            return None

    def object_data(self, value, name):
        if not isinstance(value, dict):
            self.error(name, "must be an object")
            return {}
        return value

    def source_story(self, record, where, seen_ids, seen_urls):
        self.identifier(record, where, seen_ids)
        for key in ("title", "summary", "date", "url"):
            self.text(record, key, where)
        for key in ("title_en", "summary_en", "category"):
            self.text(record, key, where, optional=True)
        value = record.get("date", "")
        try:
            if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ValueError()
            date.fromisoformat(value)
        except ValueError:
            self.error(where + ".date", "must be a real ISO date in YYYY-MM-DD format")
        url = record.get("url")
        if self.web_url(url, where + ".url"):
            normalized = url.rstrip("/")
            if normalized in seen_urls:
                self.error(where + ".url", "duplicate url: " + url)
            seen_urls.add(normalized)
        self.image(record, where, required=True, alt_required=True)

    def check_news(self, news):
        seen_ids, seen_urls = set(), set()
        records = self.objects(news, "news")
        self.counts["news"] = len(records)
        for record, where in records:
            self.source_story(record, where, seen_ids, seen_urls)
            category = record.get("category", "")
            if isinstance(category, str) and category.strip().casefold() == "opportunities":
                self.error(where + ".category", "move recruitment to opportunities.json (current/archived); recruitment does not belong in News")
        return seen_ids, seen_urls

    def check_opportunities(self, opportunities, news_ids, news_urls):
        opportunities = self.object_data(opportunities, "opportunities")
        seen_ids, seen_urls = set(), set()
        for section in ("current", "archived"):
            records = self.objects(opportunities.get(section), "opportunities." + section)
            self.counts[section + "_opportunities"] = len(records)
            if section == "current" and len(records) > 1:
                self.error("opportunities.current", "Contact currently supports at most one current announcement; combine related openings or update the Contact template first")
            for record, where in records:
                self.source_story(record, where, seen_ids, seen_urls)
                record_id, url = record.get("id"), record.get("url")
                if isinstance(record_id, str) and record_id in news_ids:
                    self.error(where + ".id", "also exists in News; move recruitment to opportunities.json and remove the News copy")
                if isinstance(url, str) and url.rstrip("/") in news_urls:
                    self.error(where + ".url", "source URL also exists in News; remove the duplicate News copy")
                if section == "current":
                    for key in ("positions", "intake", "research_focus"):
                        self.text(record, key, where)
                    self.strings(record.get("requirements"), where + ".requirements")

    def check_team(self, team):
        team = self.object_data(team, "team")
        group_ids, member_ids = set(), set()
        for group, where in self.objects(team.get("groups"), "team.groups"):
            self.identifier(group, where, group_ids, "group id")
            self.text(group, "title", where)
            for member, location in self.objects(group.get("members"), where + ".members"):
                self.identifier(member, location, member_ids, "member id")
                self.text(member, "name", location)
                self.strings(member.get("interests"), location + ".interests")
                for key in ("entry", "entry_type", "note", "education"):
                    self.text(member, key, location, optional=True)
                if group.get("id") in ("postdoc", "phd", "ra") and "entry" in member:
                    if not re.fullmatch(r"\d{4}-now", str(member["entry"])):
                        self.error(location + ".entry", "use joining-year-now, e.g. 2023-now; record graduation or role changes separately")
                if "postdoc_supervisors" in member:
                    for supervisor, supervisor_where in self.objects(
                            member["postdoc_supervisors"], location + ".postdoc_supervisors"):
                        for key in ("name", "institution"):
                            self.text(supervisor, key, supervisor_where)
                if "email" in member and not EMAIL_PATTERN.fullmatch(str(member["email"])):
                    self.error(location + ".email", "must be a valid email address")
                self.image(member, location, required=True)
        for member, where in self.objects(team.get("alumni"), "team.alumni"):
            for key in ("name", "role", "period"):
                self.text(member, key, where)
            if "id" in member:
                self.identifier(member, where, member_ids, "member id")
            self.image(member, where)
        self.counts["members"] = len(member_ids)
        return member_ids

    def check_publications(self, publications):
        paper_ids, dois, urls = set(), set(), set()
        records = self.objects(publications, "group_publications")
        self.counts["publications"] = len(records)
        for paper, where in records:
            self.identifier(paper, where, paper_ids)
            self.year(paper, "year", where)
            self.year(paper, "online_year", where, optional=True)
            for key in ("title", "journal", "volume", "locator", "doi", "url"):
                self.text(paper, key, where)
            if type(paper.get("order")) is not int:
                self.error(where + ".order", "must be an integer sort key")
            doi = paper.get("doi")
            if not isinstance(doi, str) or not DOI_PATTERN.fullmatch(doi):
                self.error(where + ".doi", "must be a bare DOI such as 10.1234/example")
            elif doi.casefold() in dois:
                self.error(where + ".doi", "duplicate doi: " + doi)
            else:
                dois.add(doi.casefold())
            url = paper.get("url")
            if self.web_url(url, where + ".url"):
                if url.casefold().rstrip("/") in urls:
                    self.error(where + ".url", "duplicate url: " + url)
                urls.add(url.casefold().rstrip("/"))
                parsed = urlsplit(url)
                if parsed.hostname in ("doi.org", "dx.doi.org") and isinstance(doi, str):
                    if unquote(parsed.path).lstrip("/").casefold() != doi.casefold():
                        self.error(where + ".url", "DOI resolver URL does not match doi")
            authors = self.objects(paper.get("authors"), where + ".authors")
            if not authors:
                self.error(where + ".authors", "at least one author is required")
            for author, location in authors:
                self.text(author, "name", location)
                self.text(author, "label", location)
                for key in ("is_pi", "corresponding"):
                    if type(author.get(key)) is not bool:
                        self.error(location + "." + key, "must be a boolean")
        return paper_ids

    def references(self, values, known, where, kind, allow_empty=True):
        references = self.strings(values, where, allow_empty=allow_empty)
        seen = set()
        for value in references:
            if value not in known:
                self.error(where, "unknown " + kind + ": " + value)
            if value in seen:
                self.error(where, "duplicate " + kind + " reference: " + value)
            seen.add(value)

    def project(self, project, where):
        for key in ("title", "funder"):
            self.text(project, key, where)
        if "source_url" in project:
            self.web_url(project["source_url"], where + ".source_url")
        self.year(project, "year", where)
        if project.get("role") not in ("PI", "Co-PI", "Co-I"):
            self.error(where + ".role", "must be PI, Co-PI or Co-I")

    def check_research(self, research, member_ids, paper_ids):
        research = self.object_data(research, "research")
        self.text(research, "intro", "research")
        project_ids, topic_ids = set(), set()
        for project, where in self.objects(research.get("projects"), "research.projects"):
            self.identifier(project, where, project_ids)
            self.project(project, where)
        if "undergraduate_projects" in research:
            project = self.object_data(research["undergraduate_projects"], "research.undergraduate_projects")
            titles = self.strings(project.get("titles"), "research.undergraduate_projects.titles")
            self.project(dict(project, title=titles[0] if titles else ""), "research.undergraduate_projects")
        for topic, where in self.objects(research.get("topics"), "research.topics"):
            self.identifier(topic, where, topic_ids)
            for key in ("title", "short_title", "question", "caption"):
                self.text(topic, key, where)
            self.strings(topic.get("paragraphs"), where + ".paragraphs")
            self.strings(topic.get("keywords"), where + ".keywords")
            self.image(topic, where, required=True, alt_required=True)
            seen_people = set()
            for person, location in self.objects(topic.get("people"), where + ".people"):
                person_id = self.identifier(person, location, seen_people, "member reference")
                self.text(person, "name", location)
                if person_id not in member_ids:
                    self.error(location + ".id", "unknown member: " + person_id)
            self.references(topic.get("paper_ids"), paper_ids, where + ".paper_ids", "paper")
            if "image_source" in topic:
                self.web_url(topic["image_source"], where + ".image_source")
            if "resource" in topic:
                resource = self.object_data(topic["resource"], where + ".resource")
                self.text(resource, "label", where + ".resource")
                self.web_url(resource.get("url"), where + ".resource.url")
        self.counts["research_topics"] = len(topic_ids)

    def check_home(self, home, paper_ids):
        home = self.object_data(home, "home")
        self.references(home.get("featured_papers"), paper_ids, "home.featured_papers", "paper")
        if type(home.get("news_limit")) is not int or home["news_limit"] < 1:
            self.error("home.news_limit", "must be a positive integer")
        for key in ("contact_heading", "contact_text"):
            self.text(home, key, "home")

    def check_lab(self, lab):
        lab = self.object_data(lab, "lab")
        for key in ("name", "wordmark", "tagline", "description", "institution", "unit", "email"):
            self.text(lab, key, "lab")
        if not EMAIL_PATTERN.fullmatch(str(lab.get("email", ""))):
            self.error("lab.email", "must be a valid email address")
        for key in ("faculty_url", "scholar_url"):
            if key in lab:
                self.web_url(lab[key], "lab." + key)
        if "address" in lab:
            self.strings(lab["address"], "lab.address")
        if "office" in lab and lab["office"] is not None:
            self.text(lab, "office", "lab")
        if "homepage" in lab:
            homepage = self.object_data(lab["homepage"], "lab.homepage")
            for key in ("eyebrow", "title", "lede"):
                self.text(homepage, key, "lab.homepage")
        if "assets" in lab:
            assets = self.object_data(lab["assets"], "lab.assets")
            for key, value in assets.items():
                self.image({"image": value}, "lab.assets." + key)
        if "affiliations" in lab:
            seen = set()
            for organization, where in self.objects(lab["affiliations"], "lab.affiliations"):
                self.identifier(organization, where, seen)
                self.text(organization, "name", where)
                self.web_url(organization.get("url"), where + ".url")
                self.image(organization, where, required=True, alt_required=True)
        if "social" in lab:
            for link, where in self.objects(lab["social"], "lab.social"):
                self.text(link, "label", where)
                self.web_url(link.get("url"), where + ".url")

    def check_delivery_images(self, manifest):
        manifest = self.object_data(manifest, "delivery_images")
        for original, delivery in manifest.items():
            where = "delivery_images[" + original + "]"
            delivery = self.object_data(delivery, where)
            self.image({"image": original, "image_web": delivery.get("src")}, where)
            for key in ("width", "height", "source_bytes", "bytes"):
                if type(delivery.get(key)) is not int or delivery[key] <= 0:
                    self.error(where + "." + key, "must be a positive integer")
        self.counts["delivery_images"] = len(manifest)

    def check_source(self):
        data = {name: self.load(name) for name in DATA_FILES}
        news_ids, news_urls = self.check_news(data["news"])
        opportunities = self.load("opportunities", optional=True)
        if opportunities is not None:
            self.check_opportunities(opportunities, news_ids, news_urls)
        member_ids = self.check_team(data["team"])
        paper_ids = self.check_publications(data["group_publications"])
        self.check_research(data["research"], member_ids, paper_ids)
        self.check_home(data["home"], paper_ids)
        lab = self.load("lab", optional=True)
        if lab is not None:
            self.check_lab(lab)
        manifest = self.load("delivery_images", optional=True)
        if manifest is not None:
            self.check_delivery_images(manifest)


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.duplicates = set()
        self.links = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        identifier = attrs.get("id")
        if identifier:
            if identifier in self.ids:
                self.duplicates.add(identifier)
            self.ids.add(identifier)
        # Named anchors remain valid fragment destinations in older Jekyll markup.
        if tag == "a" and attrs.get("name"):
            self.ids.add(attrs["name"])
        for key in ("href", "src", "poster", "data-src"):
            if attrs.get(key):
                kind = "path" if tag in ("a", "area") and key == "href" else "asset"
                self.links.append((attrs[key], kind))
        if attrs.get("srcset") and not attrs["srcset"].lstrip().startswith("data:"):
            for candidate in attrs["srcset"].split(","):
                bits = candidate.strip().split()
                if bits:
                    self.links.append((bits[0], "asset"))

    handle_startendtag = handle_starttag


def config_values(root):
    """Read only the scalar URL settings; this deliberately is not a YAML parser."""
    result = {"url": "", "baseurl": ""}
    path = root / "_config.yml"
    if path.is_file():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            match = re.match(r"^(url|baseurl)\s*:\s*(.*)$", line)
            if match:
                value = match[2].split(" #", 1)[0].strip().strip("\"'")
                result[match[1]] = "" if value in ("", "null", "~") or value.startswith("#") else value
    return result


def check_built(checker, site_dir, baseurl="", site_url=""):
    site_dir = Path(site_dir).resolve()
    baseurl = "/" + baseurl.strip("/") if baseurl.strip("/") else ""
    site_host = urlsplit(site_url).netloc.lower()
    cache = {}

    def parse(path):
        if path not in cache:
            page = PageParser()
            try:
                page.feed(path.read_text(encoding="utf-8-sig"))
            except (OSError, UnicodeError) as exc:
                checker.error(str(path), "cannot read HTML: " + str(exc))
            cache[path] = page
        return cache[path]

    for route in CORE_ROUTES:
        source = site_dir / route.strip("/") / "index.html"
        where = "built " + route
        if not source.is_file():
            checker.error(where, "missing core route: " + str(source))
            continue
        page = parse(source)
        for identifier in sorted(page.duplicates):
            checker.error(where, "duplicate HTML id: " + identifier)
        for raw, kind in page.links:
            try:
                parsed = urlsplit(raw)
                if parsed.scheme and parsed.scheme not in ("http", "https"):
                    continue
                if parsed.netloc and parsed.netloc.lower() != site_host:
                    continue
                resolved = urlsplit(urljoin("https://check.invalid" + baseurl + route, raw))
            except ValueError:
                checker.error(where, "invalid URL: " + raw)
                continue
            path = unquote(resolved.path)
            if baseurl:
                if path != baseurl and not path.startswith(baseurl + "/"):
                    checker.error(where, "internal URL is missing baseurl " + baseurl + ": " + raw)
                    continue
                path = path[len(baseurl):] or "/"
            target = (site_dir / path.lstrip("/")).resolve()
            if not target.is_relative_to(site_dir):
                checker.error(where, "internal path points outside the built site: " + raw)
                continue
            if target.is_dir() or path.endswith("/"):
                target = target / "index.html"
            if not target.is_file():
                checker.error(where, "missing " + ("asset" if kind == "asset" else "internal path") + ": " + raw)
                continue
            fragment = unquote(resolved.fragment).split(":~:text=", 1)[0]
            if fragment and kind == "path" and target.suffix.lower() in (".html", ".htm"):
                if fragment not in parse(target).ids:
                    checker.error(where, "missing fragment: " + raw)
    checker.counts["core_routes_checked"] = len(CORE_ROUTES)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1],
                        help="website source directory (default: script's parent website)")
    parser.add_argument("--site-dir", type=Path, help="also inspect a Jekyll build; relative to --root")
    parser.add_argument("--baseurl", help="override project path, e.g. /preview; defaults to _config.yml")
    parser.add_argument("--site-url", help="own site origin for absolute links; defaults to _config.yml")
    parser.add_argument("--json", action="store_true", help="write a machine-readable JSON report")
    args = parser.parse_args(argv)
    checker = ContentChecker(args.root)
    checker.check_source()
    if args.site_dir is not None:
        settings = config_values(checker.root)
        site_dir = args.site_dir if args.site_dir.is_absolute() else checker.root / args.site_dir
        check_built(checker, site_dir,
                    args.baseurl if args.baseurl is not None else settings["baseurl"],
                    args.site_url if args.site_url is not None else settings["url"])
    report = {"ok": not checker.errors, "counts": checker.counts, "errors": checker.errors}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for error in checker.errors:
            print("ERROR " + error)
        status = "FAIL" if checker.errors else "PASS"
        print(f"{status}: {len(checker.errors)} error(s); " + ", ".join(
            f"{key}={value}" for key, value in checker.counts.items()))
    return 1 if checker.errors else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
