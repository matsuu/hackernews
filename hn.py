"""
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


from xml.sax.saxutils import escape

import urllib, re, os, urlparse
import HTMLParser, feedparser
import feedgenerator
from BeautifulSoup import BeautifulSoup
from pprint import pprint

HN_RSS_FEED = u"http://news.ycombinator.com/rss"

NEGATIVE    = re.compile("comment|meta|footer|footnote|foot")
POSITIVE    = re.compile("post|hentry|entry|content|text|body|article")
PUNCTUATION = re.compile("\W")
BLOGSPOT    = re.compile(".*You can still visit a.*non-dynamic version")


def grabContent(link, html):
    
    replaceBrs = re.compile("<br */? *>\s*<br */? *>")
    html = re.sub(replaceBrs, "</p><p>", html)
    
    try:
        soup = BeautifulSoup(html)
    except HTMLParser.HTMLParseError:
        return ""
    
    # REMOVE SCRIPTS
    for s in soup.findAll("script"):
        s.extract()
    
    allParagraphs = soup.findAll("p")
    topParent     = None
    
    parents = []
    for paragraph in allParagraphs:
        
        parent = paragraph.parent
        
        if (parent not in parents):
            parents.append(parent)
            parent.score = 0
            
            if (parent.has_key("class")):
                if (NEGATIVE.match(parent["class"])):
                    parent.score -= 50
                if (POSITIVE.match(parent["class"])):
                    parent.score += 25
                    
            if (parent.has_key("id")):
                if (NEGATIVE.match(parent["id"])):
                    parent.score -= 50
                if (POSITIVE.match(parent["id"])):
                    parent.score += 25

        if (parent.score == None):
            parent.score = 0
        
        innerText = paragraph.renderContents() #"".join(paragraph.findAll(text=True))
        if (len(innerText) > 10):
            parent.score += 1
            
        parent.score += innerText.count(",")
        
    for parent in parents:
        if ((not topParent) or (parent.score > topParent.score)):
            topParent = parent

    if (not topParent):
        return ""
            
    # REMOVE LINK'D STYLES
    styleLinks = soup.findAll("link", attrs={"type" : "text/css"})
    for s in styleLinks:
        s.extract()

    # REMOVE ON PAGE STYLES
    for s in soup.findAll("style"):
        s.extract()

    # CLEAN STYLES FROM ELEMENTS IN TOP PARENT
    for ele in topParent.findAll(True):
        del(ele['style'])
        del(ele['class'])
        
    killDivs(topParent)
    clean(topParent, "form")
    clean(topParent, "object")
    clean(topParent, "iframe")
    
    fixLinks(topParent, link)
    
    return topParent.renderContents().decode('utf-8')
    

def fixLinks(parent, link):
    tags = parent.findAll(True)
    
    for t in tags:
        if (t.has_key("href")):
            t["href"] = urlparse.urljoin(link, t["href"])
        if (t.has_key("src")):
            t["src"] = urlparse.urljoin(link, t["src"])


def clean(top, tag, minWords=10000):
    tags = top.findAll(tag)

    for t in tags:
        if (t.renderContents().count(" ") < minWords):
            t.extract()


def killDivs(parent):
    
    divs = parent.findAll("div")
    for d in divs:
        p     = len(d.findAll("p"))
        img   = len(d.findAll("img"))
        li    = len(d.findAll("li"))
        a     = len(d.findAll("a"))
        embed = len(d.findAll("embed"))
        pre   = len(d.findAll("pre"))
        code  = len(d.findAll("code"))
    
        if (d.renderContents().count(",") < 10):
            if ((pre == 0) and (code == 0)):
                if ((img > p ) or (li > p) or (a > p) or (p == 0) or (embed > 0)):
                    d.extract()
    

def upgradeLink(link):
    
    if (not (link.startswith("http://news.ycombinator.com") or link.endswith(".pdf"))):
        linkFile = "upgraded/" + re.sub(PUNCTUATION, "_", link)
        if (os.path.exists(linkFile)):
            return open(linkFile).read().decode('utf-8')
        else:
            content = ""
            try:
                html = urllib.urlopen(link).read()
                content = grabContent(link, html)
                if content == "" and BLOGSPOT.match(html):
                  index = link.find("?")
                  new_link = link
                  if index > 0:
                    query_string = urlparse.parse_qs(new_link[index+1:])
                    query_string["v"] = "0"
                    new_link = new_link[:index+1] + urllib.urlencode(query_string)
                  else:
                    new_link += "?v=0"
                  html = urllib.urlopen(new_link).read()
                  content = grabContent(new_link, html)

                filp = open(linkFile, "w")
                filp.write(content.encode('utf-8'))
                filp.close()
            except IOError:
                pass
            return content
    else:
        return ""
    
    

def upgradeFeed(feedUrl):
    
    feedData = urllib.urlopen(feedUrl).read()
    
    parsedFeed = feedparser.parse(feedData)
    
    feedOutput = feedgenerator.Rss201rev2Feed(
        title=u"Hacker News",
        link=u"http://news.ycombinator.com/",
        feed_url=u"http://matsuu.org/hackernews/hackernews.html",
        description=u"Links for the intellectually curious, ranked by readers.",
        language=u"en",
    )

    for entry in parsedFeed.entries:
        content = upgradeLink(entry.link)
        feedOutput.add_item(
            title=entry.title,
            link=entry.link,
            comments=entry.comments,
            description=u"""<p><a href="%s">Comments</a></p>%s<p><a href="%s">Comments</a>""" % (entry.comments, content, entry.comments)
        )

    return feedOutput.writeString('utf-8')
    
if __name__ == "__main__":  
    print upgradeFeed(HN_RSS_FEED)


















