# BEGIN GPL LICENSE BLOCK #####
#
# This file is part of Hot Node.
#
# Hot Node is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.
#
# Hot Node is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hot Node. If not, see <https://www.gnu.org/licenses/>.
#
# END GPL LICENSE BLOCK #####


import os, difflib, time


def split_by_slash(string: str):
    '''Split the string by " / ". Note the space next to the slash will be removed.'''
    if string == "":
        return []
    keys = string.split(sep="/")
    for i in range(len(keys)):
        string: str = keys[i]
        if string.startswith(" "):
            string = string[1:]
        if string.endswith(" "):
            string = string[:-1]
        keys[i] = string
    return keys


def split_name_suffix(full_name: str):
    '''Split blender name style str into name and int suffix. Example: Obj.001 -> Obj 1. No suffix means -1.'''
    last_dot_idx = full_name.rfind('.')
    name: str = full_name
    int_suffix: int = 0
    if last_dot_idx != -1:
        name = full_name[ :last_dot_idx]
        str_suffix: str = full_name[last_dot_idx + 1: ]
        if str_suffix.isdecimal():
            int_suffix = int(str_suffix)
    return name, int_suffix


def combine_name_suffix(name: str, suffix: int):
    '''Combine name and int suffix to blender style. Example: Obj + 1 = Obj.001. Obj + -1 = Obj.'''
    if suffix == 0:
        return name
    str_suffix = str(suffix)
    str_length = len(str_suffix)
    dst_length = 3
    if str_length > 3:
        dst_length = str_length
    full_name: str = '.'.join((name, str(suffix).rjust(dst_length, '0')))
    return full_name


def find_min_vacant_number(number_list: list):
    '''Help to find the minimum number in a series of numbers, with time & space complexity O(2n).'''
    # XXX actually, blender allows Foo.000, but here we consider Foo as Foo.000.
    if number_list == []:
        return 0
    max_num = max(number_list)
    lst = [True] * (max_num + 1)
    for num in number_list:
        lst[num] = False
    for i in range(max_num + 1):
        if lst[i]:
            return i
    return max_num + 1


def ensure_unique_name_dot(new_full_name: str, new_idx: int, collection):
    '''Change <new_full_name> with blender style if re-name exists in <collection.name>, with time & space complexity O(2n).
    
    - new_idx: new_full_name's index in the collection, will be used to skip the new name itself. so if dont have new name in the name list, pass a value like -1.'''
    new_name, new_suffix = split_name_suffix(new_full_name)
    suffix_list = []
    # find all renamed preset and collect their suffix
    for i in range(len(collection)):
        if i == new_idx:
            continue
        full_name = collection[i].name
        name, suffix = split_name_suffix(full_name)
        if name == new_name:
            suffix_list.append(suffix)
    if suffix_list == []:
        return new_full_name
    # find a available suffix number. 0 means dont need suffix
    available_suffix = find_min_vacant_number(suffix_list)
    max_suffix = max(suffix_list)
    # allow user to change suffix to a bigger number
    if new_suffix <= available_suffix:
        new_suffix = available_suffix
    # if change Foo.001 to Foo.002 and Foo.002 already exists, go into this branch. The result is same as blender's rename logic.
    else:
        new_suffix = max_suffix + 1
    result = combine_name_suffix(new_name, new_suffix)
    return result


def ensure_unique_name(new_full_name: str, new_idx: int, name_list):
    '''Change <new_full_name> with blender style if re-name exists in <collection>, with time & space complexity O(2n).
    
    - new_idx: new_full_name's index in the collection, will be used to skip the new name itself. so if dont have new name in the name list, pass a value like -1.'''
    new_name, new_suffix =split_name_suffix(new_full_name)
    suffix_list = []
    # find all renamed name body and collect their suffix
    for i in range(len(name_list)):
        if i == new_idx:
            continue
        full_name = name_list[i]
        name, suffix = split_name_suffix(full_name)
        if name == new_name:
            suffix_list.append(suffix)
    if suffix_list == []:
        return new_full_name
    # find a available suffix number. 0 means dont need suffix
    available_suffix = find_min_vacant_number(suffix_list)
    max_suffix = max(suffix_list)
    # allow user to change suffix to a bigger number
    if new_suffix <= available_suffix:
        new_suffix = available_suffix
    # if change Foo.001 to Foo.002 and Foo.002 already exists, go into this branch. The result is same as blender's rename logic.
    else:
        new_suffix = max_suffix + 1
    result = combine_name_suffix(new_name, new_suffix)
    return result


def ensure_has_suffix(name: str, suffix: str):
    length = len(suffix)
    if name[-length:] != suffix:
        return ''.join((name, suffix))
    else:
        return name
    
    
def find_name_body_before_words(name_body: str, name_list: list[str], beford_words: str):
    '''Find is there a name whose name_body before the first <before_words>, return the existing full name or return False if there is no such a name.'''
    for existing_name in name_list:
        split_idx = existing_name.find(beford_words)
        if split_idx != -1:
            existing_name_body = existing_name[:split_idx]
            if name_body == existing_name_body:
                return existing_name
    return False


def find_name_body_after_words(name_body: str, name_list: list[str], after_words: str):
    '''Find is there a name whose name_body after the first <after_words>, return the existing full name or return False if there is no such a name.'''
    for existing_name in name_list:
        split_idx = existing_name.find(after_words)
        if split_idx != -1:
            existing_name_body = existing_name[:split_idx]
            if name_body == existing_name_body:
                return existing_name
    return False


def find_string_between_words(string: str, after_words: str|None, beford_words: str|None):
    '''Find is there a string between the LAST <after_words> and the FIRST <before_words>, 
    return the string or return False if there is no such a string.
    Keep <after_words> / <before_words> None to get unilateral split.
    '''
    if after_words is None:
        first_idx = 0
    else:
        first_idx = string.rfind(after_words)
        if first_idx == -1:
            return False
        first_idx = string.rfind(after_words) + len(after_words)
        
    if beford_words is None:
        # [:] will exclude last_idx, [:) in fact
        last_idx = len(string)
    else:
        last_idx = string.find(beford_words)
        if last_idx == -1:
            return False
    if last_idx > first_idx:
        return string[first_idx:last_idx]
    return False

    
def list_cattr(cobj: dict, attr_name: str):
    '''Get all cobj's elements' attr as a list'''
    result_list = []
    for item in cobj.values():
        result = item.get(attr_name, None)
        result_list.append(result)
    return result_list
    
    
def get_average_vector(vector_list: list) -> list:
    length = len(vector_list)
    dimension = len(vector_list[0])
    result_vector = [0.0] * dimension
    for vector in vector_list:
        for i in range(dimension):
            result_vector[i] += vector[i]
    for i in range(dimension):
            result_vector[i] /= length
    return result_vector


def float_list_minus(list1, list2):
    length = len(list1)
    result = [0.0] * length
    for i in range(length):
        result[i] = list1[i] - list2[i]
    return result


def diff_ratio(str1: str, str2: str):
    '''Compare two strings' difference ratio, 1 means totally same and 0 means totally different.'''
    return difflib.SequenceMatcher(None, str1, str2).ratio()


def get_similar_str(example_str:str, str_list: list, tolerance=0.99):
    '''Return the string which is most similar to the example_str and whose similar ratio is more than the 1 - tolerance in the str_list.'''
    best_ratio = 0.0
    best_str = None
    for i in range(len(str_list)):
        ratio = difflib.SequenceMatcher(None, example_str, str_list[i]).ratio()
        if ratio > best_ratio and ratio > 1 - tolerance:
            best_str = str_list[i]
            best_ratio = ratio
    return best_str


def get_autosave_time_str():
    '''Return: DDHHMM with blanks filled by 0'''
    timestamp = time.time()
    local_time = time.localtime(timestamp)
    day = str(local_time.tm_mday).rjust(2, "0")
    hour = str(local_time.tm_hour).rjust(2, "0")
    minute = str(local_time.tm_min).rjust(2, "0")
    autosave_time_str = "".join((day, hour, minute))
    return autosave_time_str


def get_autosave_time():
    '''[D, H, M]'''
    timestamp = time.time()
    local_time = time.localtime(timestamp)
    return [local_time.tm_mday, local_time.tm_hour, local_time.tm_min]


def parse_autosave_time_str(autosave_time_str):
    day = int(autosave_time_str[0:2])
    hour = int(autosave_time_str[2:4])
    minute = int(autosave_time_str[4:6])
    return [day, hour, minute]


def compare_size_same(file_path1: str, file_path2: str, tolerance: int=4):
    '''Compare whether the file are same by file size delta < tolerance bytes'''
    size1 = os.path.getsize(file_path1)
    size2 = os.path.getsize(file_path2)
    delta = size1 - size2
    if tolerance > 0:
        if -tolerance < delta < tolerance:
            return True
        else:
            return False
    else:
        if delta == 0:
            return True
        else:
            return False
        

def exchange_idx(list, idx1, idx2):
    temp = list[idx1]
    list[idx1] = list[idx2]
    list[idx2] = temp