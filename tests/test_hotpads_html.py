import sys,os,glob;_T=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));sys.path.insert(0,os.path.join(_T,"src") if os.path.exists(os.path.join(_T,"src","scout.py")) else _T);import scout
def test_html_card():
    h='<a href="https://hotpads.com/100-example-ave-town-ca-90001-1abc0x0/c/pad?nid=x"><div>$3,400/mo</div><div>2 beds</div><div>100 Example Ave #C</div><div>Town, CA 90001</div></a><a href="https://hotpads.com/100-example-ave-town-ca-90001-1abc0x0/c/pad?contactModal=true">Contact</a>'
    L=scout._parse_hotpads_text(scout._hotpads_html_to_text(h),"t")
    assert len(L)==1 and L[0]["id"]=="email:addr:100-elm-c" and L[0]["price"]==3400 and L[0]["beds"]==2
    assert L[0]["url"]=="https://hotpads.com/100-example-ave-town-ca-90001-1abc0x0/c/pad"
def test_saved_emails_have_links():
    for f in glob.glob(os.path.join(os.path.dirname(scout.__file__),"inbox","hotpads-*sparkpost.txt")):
        for l in scout.parse_email_file(f): assert l["url"]
