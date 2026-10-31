import sys,os;_T=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));sys.path.insert(0,os.path.join(_T,"src") if os.path.exists(os.path.join(_T,"src","scout.py")) else _T);import scout
B="""* Rental that matches your search for: X *
1. NEW: 200 Sample Way, Town, CA 90001
- Price: $2,899/mo
- Details: 2 Beds, 2 Baths, 1,008 Sq. Ft.
- Additional Details: https://www.redfin.com/CA/Town/200-Sample-Way-90001/home/1000001?utm=x
* Nearby similar homes *
1. NEW: 300 Demo Dr E, Town, CA 90001
- Price: $2,222-$3,769/mo
- Additional Details: https://www.redfin.com/CA/Town/300/home/1
"""
def test_parse():
    assert scout.is_redfin_list_text(B)
    L=scout._parse_redfin_list_text(B,"t")
    assert len(L)==1; l=L[0]
    assert l["id"]=="email:addr:200-sample" and l["price"]==2899 and l["beds"]==2 and l["baths"]==2 and l["sqft"]==1008
    assert l["url"]=="https://www.redfin.com/CA/Town/200-Sample-Way-90001/home/1000001" and l["zip"]=="90001"
def test_no_link_dropped():
    assert scout._parse_redfin_list_text(B.replace("- Additional Details: https://www.redfin.com/CA/Town/200-Sample-Way-90001/home/1000001?utm=x\n",""),"t")==[]
if __name__=="__main__": test_parse(); test_no_link_dropped(); print("ok")
