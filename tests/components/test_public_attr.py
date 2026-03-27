from tetra import Component, public

def test_public_decorated_attribute():
    class MyComponent(Component):
        my_attr = public('initial')
        template = '<div></div>'
    
    assert 'my_attr' in MyComponent._public_properties
    c = MyComponent(None)
    assert c.my_attr == 'initial'
    assert c._data()['my_attr'] == 'initial'