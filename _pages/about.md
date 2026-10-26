---
layout: lab
permalink: /
title: "LogScience Lab"
section: home
home: true
sitemap: true
description: "Groundwater science from river basins to the coast. Discover the research, people and latest work of the LogScience Lab at HKUST(GZ)."
redirect_from:
  - /about/
  - /about.html
---
{% assign lab = site.data.lab %}
<section class="home-hero shell">
  <div class="hero-copy"><div><p class="eyebrow">{{ lab.homepage.eyebrow }}</p><h1>{{ lab.homepage.title }}</h1></div><div><p class="lede">{{ lab.homepage.lede }}</p><div class="button-row"><a class="button" href="{{ '/research/' | relative_url }}">Explore our research <span aria-hidden="true">↗</span></a><a class="button button--light" href="#latest-news">Latest from the lab <span aria-hidden="true">↓</span></a></div></div></div>
  {% include lab-carousel.html photos=site.data.home.gallery variant="home" label="Life at LogScience Lab" interval=2000 captions=false controls="dots" autoplay=true %}
  <div class="methods-strip" aria-label="Our methods"><span>Field observations</span><span>Isotope tracing</span><span>Laboratory experiments</span><span>Numerical modeling</span><span>Satellite remote sensing</span></div>
</section>
<section class="section shell" id="latest-news" aria-labelledby="latest-title">
  <div class="section-head"><div><p class="eyebrow">Research & community</p><h2 id="latest-title">Latest from the lab</h2></div><a class="text-link" href="{{ '/news/' | relative_url }}">All news <span aria-hidden="true">↗</span></a></div>
  <div class="news-tiles">{% assign recent = site.data.news | sort: 'date' | reverse %}{% for item in recent limit:site.data.home.news_limit %}{% include lab-news-tile.html item=item %}{% endfor %}</div>
</section>
<section class="section research-preview"><div class="shell"><div><p class="eyebrow">What we study</p><h2>Research themes</h2><p>From mineral reactions and groundwater exchange to entire river networks, we connect measurements with models to understand environmental processes.</p><a class="text-link" href="{{ '/research/' | relative_url }}">Questions, methods & findings <span aria-hidden="true">↗</span></a></div><ol class="theme-index">{% for topic in site.data.research.topics %}<li><a href="{{ '/research/' | relative_url }}#{{ topic.id }}"><small>{{ topic.number }}</small><strong>{{ topic.short_title }}</strong><span aria-hidden="true">↗</span></a></li>{% endfor %}</ol></div></section>
<section class="section shell" aria-labelledby="selected-title"><div class="section-head"><div><p class="eyebrow">Selected work</p><h2 id="selected-title">Publications</h2></div><a class="text-link" href="{{ '/publications/' | relative_url }}">Complete group collection <span aria-hidden="true">↗</span></a></div><ul class="selected-papers">{% for id in site.data.home.featured_papers %}{% assign paper = site.data.group_publications | where: 'id', id | first %}<li class="selected-paper"><p class="journal">{{ paper.journal }}<span>{{ paper.year }}</span></p><h3><a href="{{ paper.url }}" target="_blank" rel="noopener noreferrer">{{ paper.title }} <span aria-hidden="true">↗</span></a></h3></li>{% endfor %}</ul></section>
<section class="shell"><div class="team-preview"><div>{% include lab-image.html src=lab.assets.field alt="Team members collecting water samples in the field" %}</div><div class="team-preview__text"><p class="eyebrow">Our people</p><h2>Science is a collaborative effort.</h2><p>Led by Yi LIU, our team brings together expertise in hydrogeology, biogeochemistry, contaminant transport and environmental data analysis.</p><a class="text-link" href="{{ '/team/' | relative_url }}">Meet the team <span aria-hidden="true">↗</span></a></div></div><div class="contact-strip"><div><h2>{{ site.data.home.contact_heading | escape }}</h2><p>{{ site.data.home.contact_text | escape }}</p></div><a class="button button--light" href="{{ '/contact/' | relative_url }}">Contact the lab <span aria-hidden="true">↗</span></a></div></section>

<section class="affiliations shell" aria-labelledby="affiliations-title"><div class="affiliations-heading"><h2 id="affiliations-title">Institution & research networks</h2></div><div class="affiliations-logos">{% for organization in site.data.lab.affiliations %}<a class="affiliation-logo affiliation-logo--{{ organization.id }}" href="{{ organization.url }}" target="_blank" rel="noopener noreferrer">{% include lab-image.html src=organization.image alt=organization.image_alt %}</a>{% endfor %}</div></section>
