"""Regression checks for the portable content CLI (standard library only)."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CHECKER = Path(__file__).resolve().parents[1] / "tools" / "check_content.py"
ROUTES = ("", "research", "team", "publications", "platform", "news", "contact")


class ContentChecksTest(unittest.TestCase):
    def setUp(self):
        # Keep fixtures in the writable checkout, including restricted Windows sessions.
        self.temp = tempfile.TemporaryDirectory(prefix=".content-check-", dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "_data").mkdir()
        (self.root / "images").mkdir()
        (self.root / "images" / "sample.svg").write_text("<svg/>", encoding="utf-8")
        self.data = {
            "news": [{"id": "news-new", "date": "2026-10-26", "title": "News",
                      "summary": "Confirmed source summary", "url": "https://example.org/news/1",
                      "image": "/images/sample.svg", "image_alt": "Field site"}],
            "team": {"groups": [{"id": "pi", "title": "Principal Investigator",
                                  "members": [{"id": "member-1", "name": "A Person",
                                               "image": "/images/sample.svg",
                                               "interests": ["Water"], "entry": "2023"}]}],
                     "alumni": [{"name": "Former Person", "role": "Student", "period": "2024"}]},
            "group_publications": [{"id": "paper-new", "year": 2026, "order": 1,
                                    "title": "A paper", "journal": "A journal", "volume": "1",
                                    "locator": "12", "doi": "10.1234/example.1",
                                    "url": "https://doi.org/10.1234/example.1",
                                    "authors": [{"name": "A Person", "label": "Person, A.",
                                                 "is_pi": True, "corresponding": True}]}],
            "research": {"intro": "Research overview", "projects": [
                {"id": "project-1", "title": "Project", "funder": "Funder", "year": 2026, "role": "Co-I"}],
                "topics": [{"id": "theme-1", "number": "01", "title": "Theme",
                            "short_title": "Theme", "question": "What happens?",
                            "paragraphs": ["Public research aims"], "keywords": ["Water"],
                            "people": [{"id": "member-1", "name": "A Person"}],
                            "paper_ids": ["paper-new"], "image": "/images/sample.svg",
                            "image_alt": "Conceptual workflow", "caption": "Conceptual figure"}]},
            "home": {"news_limit": 3, "featured_papers": ["paper-new"],
                     "contact_heading": "Contact", "contact_text": "Get in touch"},
        }

    def write_data(self):
        for name, value in self.data.items():
            (self.root / "_data" / (name + ".json")).write_text(
                json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def run_check(self, *args):
        self.write_data()
        return subprocess.run([sys.executable, str(CHECKER), "--root", str(self.root), *args],
                              text=True, encoding="utf-8", capture_output=True, check=False)

    def assert_fails(self, needle, *args):
        result = self.run_check(*args)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(needle, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def build_site(self, prefix=""):
        site = self.root / "_site"
        for route in ROUTES:
            path = site / route / "index.html"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                '<html><head><link href="' + prefix + '/assets/main.css" rel="stylesheet"></head>'
                '<body id="top"><a href="' + prefix + '/research/#topic">Theme</a>'
                '<img src="' + prefix + '/images/sample.svg" alt="Field">'
                '<section id="topic"></section></body></html>', encoding="utf-8")
        (site / "assets").mkdir()
        (site / "assets" / "main.css").write_text("body{}", encoding="utf-8")
        (site / "images").mkdir()
        (site / "images" / "sample.svg").write_text("<svg/>", encoding="utf-8")
        return site

    def test_valid_small_dataset_does_not_require_fixed_counts_or_semesters(self):
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_alumni_can_record_confirmed_period_and_destination_before_role_is_known(self):
        self.data["team"]["alumni"] = [{"name": "Former Person", "period": "Summer 2025",
                                          "destination": "MPhil, Example University"}]
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_alumni_destination_must_be_text_when_provided(self):
        self.data["team"]["alumni"][0]["destination"] = {"unknown": True}
        self.assert_fails("destination")

    def test_local_news_story_requires_an_existing_matching_permalink(self):
        self.data["news"][0].update(url="/news/milestone/", link_type="internal")
        page = self.root / "_pages" / "milestone.md"
        page.parent.mkdir()
        page.write_text('---\nlayout: lab\npermalink: /news/milestone/\n---\nA real story.', encoding="utf-8")
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        page.write_text('---\npermalink: /news/other/\n---\n', encoding="utf-8")
        self.assert_fails("missing local news page")

    def test_internal_news_rejects_network_and_escaping_paths(self):
        self.data["news"][0]["link_type"] = "internal"
        for bad in ("//outside.example/news/", "/news/../../secret/", "/news/%2e%2e/private/", "https://outside.example/"):
            with self.subTest(url=bad):
                self.data["news"][0]["url"] = bad
                self.assert_fails("local news URL")

    def test_carousel_gallery_checks_each_photo_and_alt(self):
        self.data["news"][0]["gallery"] = [
            {"image": "/images/sample.svg", "image_alt": "Student one", "caption": "First defense"},
            {"image": "/images/absent.jpg", "image_alt": "Student two", "caption": "Second defense"}]
        self.assert_fails("missing local image")
        self.data["news"][0]["gallery"][1] = {"image": "/images/sample.svg", "caption": "Second defense"}
        self.assert_fails("image_alt")

    def test_home_carousel_checks_gallery_images(self):
        self.data["home"]["gallery"] = [{"image": "/images/absent.jpg", "image_alt": "Team", "caption": "In the field"}]
        self.assert_fails("missing local image")

    def test_empty_platform_is_allowed_but_invalid_resource_link_is_rejected(self):
        self.data["platform"] = {"intro": "Resources", "sections": [{"id": "tools", "title": "Tools", "description": "Methods", "empty": "To be added", "items": []}]}
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.data["platform"]["sections"][0]["items"] = [{"title": "Method", "summary": "Details", "url": "javascript:alert(1)"}]
        self.assert_fails("absolute HTTP(S)")

    def platform_fixture(self, item):
        self.data["platform"] = {"intro": "Resources", "sections": [{"id": "datasets", "title": "Datasets", "description": "Forthcoming data", "empty": "To be added", "items": [item]}]}

    def test_unreleased_dataset_cannot_offer_a_download(self):
        self.platform_fixture({"title": "PRB reflectance", "summary": "Planned", "status": "planned", "download_url": "https://example.org/data.zip"})
        self.assert_fails("unreleased dataset")
        self.data["platform"]["sections"][0]["items"][0]["status"] = "in-development"
        self.assert_fails("unreleased dataset")

    def test_released_dataset_accepts_valid_download_but_rejects_unknown_status(self):
        self.platform_fixture({"title": "PRB reflectance", "summary": "Released", "status": "released", "download_url": "https://example.org/data.zip"})
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.data["platform"]["sections"][0]["items"][0]["status"] = "coming-soon-maybe"
        self.assert_fails("dataset status")

    def test_platform_metadata_and_reference_links_are_validated(self):
        self.platform_fixture({"title": "Water fraction", "summary": "Monthly water", "facts": [{"label": "Period"}], "links": [{"label": "Reference", "url": "javascript:alert(1)"}]})
        self.assert_fails(".facts[0].value")
        self.assert_fails("absolute HTTP(S)")

    def test_shared_facility_instrument_photos_are_validated(self):
        self.platform_fixture({"title": "Fe method", "summary": "Method"})
        self.data["platform"]["sections"][0]["facility"] = {"name": "EESRF", "summary": "Shared facility", "url": "https://example.org/", "equipment_url": "https://example.org/equipment/", "instruments": [{"title": "TOC/TN analyzer", "summary": "Carbon and nitrogen", "image": "/images/missing.jpg", "image_alt": "Analyzer"}]}
        self.assert_fails("missing local image")

    def test_graduate_profiles_check_images_dates_and_committees(self):
        student = {"name": "A Person", "title": "Aquatic carbon", "paragraph": "A defense", "date": "2026-07-24", "time": "09:00", "venue": "E3-202", "image": "/images/absent.jpg", "image_alt": "Defense photo", "committee": []}
        self.data["milestones"] = {"mphil_2026": {"intro": "Graduation", "students": [student]}}
        self.assert_fails("missing local image")
        student.update(image="/images/sample.svg", date="2026-02-30")
        self.assert_fails("real ISO date")
        student.update(date="2026-07-24")
        self.assert_fails("committee")

    def test_duplicate_news_ids_and_urls_are_reported(self):
        self.data["news"].append(dict(self.data["news"][0]))
        self.assert_fails("duplicate id")
        self.assert_fails("duplicate url")

    def test_invalid_calendar_date_is_reported(self):
        self.data["news"][0]["date"] = "2026-02-30"
        self.assert_fails("YYYY-MM-DD")

    def test_non_padded_date_is_reported(self):
        self.data["news"][0]["date"] = "2026-1-2"
        self.assert_fails("YYYY-MM-DD")

    def test_bad_record_shape_has_actionable_error(self):
        self.data["news"] = ["wrong"]
        self.assert_fails("must be an object")

    def test_missing_required_news_facts_are_reported(self):
        del self.data["news"][0]["summary"]
        self.assert_fails("summary")

    def test_missing_image_web_is_reported(self):
        self.data["news"][0]["image_web"] = "/images/missing.webp"
        self.assert_fails("image_web")

    def test_source_image_cannot_escape_site_root(self):
        self.data["news"][0]["image"] = "/../outside.png"
        self.assert_fails("outside")

    def test_optional_english_and_category_fields_are_supported(self):
        self.data["news"][0].update(title_en="English title", summary_en="English summary", category="Award",
                                    image_web="/images/sample.svg")
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def opportunity(self):
        record = dict(self.data["news"][0])
        record.update(id="opportunity-new", url="https://example.org/opportunity/1",
                      category="opportunities", positions="PhD students", intake="Fall 2027",
                      research_focus="Watershed biogeochemistry", requirements=["Relevant background"])
        return record

    def test_recruitment_category_in_news_has_clear_migration_error(self):
        self.data["news"][0]["category"] = "opportunities"
        self.assert_fails("move recruitment to opportunities.json")

    def test_current_and_archived_opportunities_are_supported(self):
        current = self.opportunity()
        archived = dict(current, id="opportunity-old", url="https://example.org/opportunity/old")
        for key in ("positions", "intake", "research_focus", "requirements"):
            del archived[key]
        self.data["opportunities"] = {"current": [current], "archived": [archived]}
        result = self.run_check("--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["counts"]["current_opportunities"], 1)

    def test_current_opportunities_require_confirmed_recruitment_details(self):
        current = self.opportunity()
        for key in ("positions", "intake", "research_focus", "requirements"):
            del current[key]
        self.data["opportunities"] = {"current": [current], "archived": []}
        for key in ("positions", "intake", "research_focus", "requirements"):
            self.assert_fails("opportunities.current[0]." + key)

    def test_contact_rejects_multiple_current_announcements_instead_of_hiding_one(self):
        current = self.opportunity()
        another = dict(current, id="opportunity-two", url="https://example.org/opportunity/2")
        self.data["opportunities"] = {"current": [current, another], "archived": []}
        self.assert_fails("Contact currently supports at most one current announcement")

    def test_opportunity_dates_and_source_urls_are_checked(self):
        current = self.opportunity()
        current.update(date="2026-02-30", url="not-a-url")
        self.data["opportunities"] = {"current": [current], "archived": []}
        self.assert_fails("YYYY-MM-DD")
        self.assert_fails("absolute HTTP(S) URL")

    def test_opportunity_ids_and_urls_are_unique_across_current_and_archived(self):
        current = self.opportunity()
        self.data["opportunities"] = {"current": [current], "archived": [dict(current)]}
        self.assert_fails("duplicate id")
        self.assert_fails("duplicate url")

    def test_opportunities_cannot_duplicate_news_ids_or_sources(self):
        current = self.opportunity()
        current.update(id=self.data["news"][0]["id"], url=self.data["news"][0]["url"])
        self.data["opportunities"] = {"current": [current], "archived": []}
        self.assert_fails("also exists in News")

    def test_optional_member_education_and_joint_supervisors_are_supported(self):
        member = self.data["team"]["groups"][0]["members"][0]
        member.update(education="PhD, 22Fall–2025", postdoc_supervisors=[
            {"name": "Prof. First", "institution": "University One"},
            {"name": "Prof. Second", "institution": "University Two"}])
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_current_member_tenure_uses_joining_year_now(self):
        group = self.data["team"]["groups"][0]
        group["id"] = "postdoc"
        group["members"][0]["entry"] = "25Fall"
        self.assert_fails("joining-year-now")
        group["members"][0]["entry"] = "2022-now"
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_supervisors_require_names_and_institutions(self):
        member = self.data["team"]["groups"][0]["members"][0]
        member["postdoc_supervisors"] = [{"name": "Prof. First"}]
        self.assert_fails("postdoc_supervisors[0].institution")

    def test_unknown_research_person_and_paper_are_reported(self):
        topic = self.data["research"]["topics"][0]
        topic["people"][0]["id"] = "missing-person"
        topic["paper_ids"] = ["missing-paper"]
        self.assert_fails("unknown member")
        self.assert_fails("unknown paper")

    def test_invalid_doi_is_reported(self):
        self.data["group_publications"][0]["doi"] = "not a DOI"
        self.assert_fails("doi")

    def test_doi_url_must_match_doi(self):
        self.data["group_publications"][0]["url"] = "https://doi.org/10.1234/different"
        self.assert_fails("does not match doi")

    def test_distinct_online_and_citation_years_are_valid(self):
        self.data["group_publications"][0]["online_year"] = 2025
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_publication_sort_order_allows_zero_and_negative_values(self):
        # Added papers intentionally sort ahead of the CV's numbered records.
        for order in (0, -1):
            with self.subTest(order=order):
                self.data["group_publications"][0]["order"] = order
                result = self.run_check()
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_json_report_is_machine_readable(self):
        result = self.run_check("--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["counts"]["publications"], 1)

    def test_lab_assets_and_email_are_checked(self):
        self.data["lab"] = {
            "name": "LogScience", "wordmark": "LogScience", "tagline": "Water science",
            "description": "Research group", "institution": "University", "unit": "Unit",
            "email": "invalid", "assets": {"hero": "/images/absent.webp"}, "office": None,
        }
        self.assert_fails("lab.email")
        self.assert_fails("lab.assets.hero")

    def test_valid_lab_branding_and_contact_are_supported(self):
        self.data["lab"] = {
            "name": "LogScience", "wordmark": "LogScience", "tagline": "Water science",
            "description": "Research group", "institution": "University", "unit": "Unit",
            "email": "lab@example.org", "assets": {"hero": "/images/sample.svg"},
            "office": None, "address": ["Public address"],
            "homepage": {"eyebrow": "Lab", "title": "Water", "lede": "Research"},
            "social": [{"label": "Profile", "url": "https://example.org/profile"}],
        }
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_delivery_manifest_checks_source_and_optimized_images(self):
        self.data["delivery_images"] = {
            "/images/missing-original.png": {"src": "/images/missing-web.webp", "width": 100,
                                             "height": 100, "source_bytes": 200, "bytes": 100}}
        self.assert_fails("missing-original.png")
        self.assert_fails("missing-web.webp")

    def test_valid_delivery_manifest_is_supported(self):
        self.data["delivery_images"] = {
            "/images/sample.svg": {"src": "/images/sample.svg", "width": 100,
                                    "height": 100, "source_bytes": 6, "bytes": 6}}
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_author_flags_must_be_boolean(self):
        self.data["group_publications"][0]["authors"][0]["is_pi"] = "true"
        self.assert_fails("boolean")

    def test_member_ids_are_unique_across_role_groups(self):
        self.data["team"]["groups"].append({"id": "visiting", "title": "Visitors",
                                           "members": [dict(self.data["team"]["groups"][0]["members"][0])]})
        self.assert_fails("duplicate member id")

    def test_new_role_group_is_allowed(self):
        self.data["team"]["groups"].append({"id": "visiting", "title": "Visitors", "members": []})
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_project_role_must_preserve_pi_co_pi_co_i(self):
        self.data["research"]["projects"][0]["role"] = "Lead"
        self.assert_fails("PI, Co-PI or Co-I")

    def test_undergraduate_programs_preserve_their_individual_years(self):
        self.data["research"]["undergraduate_projects"] = [
            {"funder": "X-Program", "year": 2025, "role": "PI", "titles": ["Project one", "Project two", "Project three"]},
            {"funder": "UBRTP", "year": 2024, "role": "PI", "status": "Completed", "titles": ["Terrestrial contaminant loading"]}]
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.data["research"]["undergraduate_projects"][1]["year"] = "unknown"
        self.assert_fails(".year")

    def test_home_featured_paper_must_exist(self):
        self.data["home"]["featured_papers"] = ["missing-paper"]
        self.assert_fails("unknown paper")

    def test_duplicate_json_keys_are_not_silently_overwritten(self):
        self.write_data()
        (self.root / "_data" / "news.json").write_text('[{"id":"first","id":"second"}]', encoding="utf-8")
        result = subprocess.run([sys.executable, str(CHECKER), "--root", str(self.root)],
                                text=True, encoding="utf-8", capture_output=True, check=False)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("duplicate JSON key", result.stdout)

    def test_valid_core_built_routes_and_fragments(self):
        site = self.build_site()
        result = self.run_check("--site-dir", str(site))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_built_duplicate_ids_are_reported(self):
        site = self.build_site()
        (site / "news" / "index.html").write_text('<p id="repeat"></p><p id="repeat"></p>', encoding="utf-8")
        self.assert_fails("duplicate HTML id", "--site-dir", str(site))

    def test_built_missing_path_and_asset_are_reported(self):
        site = self.build_site()
        (site / "index.html").write_text('<a href="/missing/">Bad</a><img src="/images/missing.png">', encoding="utf-8")
        self.assert_fails("missing internal path", "--site-dir", str(site))
        self.assert_fails("missing asset", "--site-dir", str(site))

    def test_built_missing_fragment_is_reported(self):
        site = self.build_site()
        (site / "team" / "index.html").write_text('<a href="/research/#missing">Bad</a>', encoding="utf-8")
        self.assert_fails("missing fragment", "--site-dir", str(site))

    def test_built_relative_paths_srcset_and_legacy_scope(self):
        site = self.build_site()
        (site / "team" / "index.html").write_text(
            '<a href="../research/?mode=list#topic">Theme</a>'
            '<img srcset="../images/sample.svg 1x, ../images/sample.svg 2x">'
            '<a href="https://external.invalid/missing">External</a>', encoding="utf-8")
        (site / "legacy").mkdir()
        (site / "legacy" / "index.html").write_text('<img src="/absent.png">', encoding="utf-8")
        result = self.run_check("--site-dir", str(site))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_built_baseurl_and_same_site_absolute_links(self):
        site = self.build_site("/preview")
        (site / "contact" / "index.html").write_text(
            '<a href="https://lab.example/preview/research/#topic">Theme</a>', encoding="utf-8")
        result = self.run_check("--site-dir", str(site), "--baseurl", "/preview", "--site-url", "https://lab.example")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_built_root_link_missing_baseurl_is_reported(self):
        site = self.build_site("/preview")
        (site / "index.html").write_text('<a href="/team/">Bad project-site link</a>', encoding="utf-8")
        self.assert_fails("baseurl", "--site-dir", str(site), "--baseurl", "/preview")

    def test_missing_core_route_is_reported(self):
        site = self.build_site()
        (site / "contact" / "index.html").unlink()
        self.assert_fails("core route", "--site-dir", str(site))


if __name__ == "__main__":
    unittest.main()
