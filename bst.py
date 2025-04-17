# bst.py
class Node:
    def __init__(self, key, value, color=True):
        self.key = key
        self.value = value
        self.left = None
        self.right = None
        self.parent = None
        self.color = color  # True for red, False for black


class RedBlackTree:
    def __init__(self):
        self.NIL = Node(None, None, False)  # NIL node is black
        self.root = self.NIL
    
    def insert(self, key, value):
        # Create new node
        new_node = Node(key, value, True)  # New nodes are red
        new_node.left = self.NIL
        new_node.right = self.NIL
        
        # Perform standard BST insert
        y = None
        x = self.root
        
        while x != self.NIL:
            y = x
            if new_node.key < x.key:
                x = x.left
            elif new_node.key > x.key:
                x = x.right
            else:
                # Key already exists, update value
                x.value = value
                return
        
        new_node.parent = y
        if y is None:
            self.root = new_node
        elif new_node.key < y.key:
            y.left = new_node
        else:
            y.right = new_node
            
        # If root, color it black and return
        if new_node.parent is None:
            new_node.color = False
            return
            
        # If grandparent is None, return
        if new_node.parent.parent is None:
            return
            
        # Fix Red-Black tree properties
        self._fix_insert(new_node)
    
    def _fix_insert(self, k):
        while k != self.root and k.parent.color == True:
            if k.parent == k.parent.parent.right:
                u = k.parent.parent.left
                if u.color == True:
                    u.color = False
                    k.parent.color = False
                    k.parent.parent.color = True
                    k = k.parent.parent
                else:
                    if k == k.parent.left:
                        k = k.parent
                        self._right_rotate(k)
                    k.parent.color = False
                    k.parent.parent.color = True
                    self._left_rotate(k.parent.parent)
            else:
                u = k.parent.parent.right
                if u.color == True:
                    u.color = False
                    k.parent.color = False
                    k.parent.parent.color = True
                    k = k.parent.parent
                else:
                    if k == k.parent.right:
                        k = k.parent
                        self._left_rotate(k)
                    k.parent.color = False
                    k.parent.parent.color = True
                    self._right_rotate(k.parent.parent)
            if k == self.root:
                break
        self.root.color = False
    
    def _left_rotate(self, x):
        y = x.right
        x.right = y.left
        
        if y.left != self.NIL:
            y.left.parent = x
            
        y.parent = x.parent
        
        if x.parent is None:
            self.root = y
        elif x == x.parent.left:
            x.parent.left = y
        else:
            x.parent.right = y
            
        y.left = x
        x.parent = y
    
    def _right_rotate(self, x):
        y = x.left
        x.left = y.right
        
        if y.right != self.NIL:
            y.right.parent = x
            
        y.parent = x.parent
        
        if x.parent is None:
            self.root = y
        elif x == x.parent.right:
            x.parent.right = y
        else:
            x.parent.left = y
            
        y.right = x
        x.parent = y
    
    def search(self, key):
        return self._search_helper(self.root, key)
    
    def _search_helper(self, node, key):
        if node == self.NIL:
            return None
        
        if key == node.key:
            return node.value
        
        if key < node.key:
            return self._search_helper(node.left, key)
        
        return self._search_helper(node.right, key)
    
    def inorder_traversal(self):
        result = []
        self._inorder_helper(self.root, result)
        return result
    
    def _inorder_helper(self, node, result):
        if node != self.NIL:
            self._inorder_helper(node.left, result)
            result.append((node.key, node.value))
            self._inorder_helper(node.right, result)