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


import os, difflib


def split_by_slash(string: str):
    '''Split the string by " / ". Note the space next to the slash will be removed.'''
    if string == "":
        return []
    keys = string.split(sep="/")
    for i in range(len(keys)):
        string: str = keys[i]
        print(string)
        if string.startswith(" "):
            string = string[1:]
        if string.endswith(" "):
            string = string[:-1]
        keys[i] = string
    return keys


def split_name_suffix(full_name: str):
    '''Split blender name style str into name and int suffix. Example: Obj.001 -> Obj 1'''
    last_dot_idx = full_name.rfind('.')
    name: str = full_name
    int_suffix: int = 0
    if last_dot_idx != -1:
        name = full_name[ : last_dot_idx]
        str_suffix: str = full_name[last_dot_idx + 1: ]
        if str_suffix.isdecimal():
            int_suffix = int(str_suffix)
    return name, int_suffix


def combine_name_suffix(name: str, suffix: int):
    '''Combine name and int suffix to blender style. Example: Obj + 1 = Obj.001.'''
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
    '''Help to find the minimum number in a series of numbers, with time & space complexity O(n).'''
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
    '''Change <new_full_name> with blender style if re-name exists in <collection.name>, with time & space complexity O(n).
    
    - new_idx: new_full_name's index in the collection, will be used to skip the new name itself. so if dont have new name in the name list, pass a value like -1.'''
    new_name, new_suffix =split_name_suffix(new_full_name)
    suffix_list = []
    # find all renamed preset and collect their suffix
    for i in range(len(collection)):
        if i == new_idx:
            continue
        full_name = collection[i].name
        name, suffix = split_name_suffix(full_name)
        if name == new_name:
            suffix_list.append(suffix)
    # find a available suffix number. 0 means dont need suffix
    available_suffix = find_min_vacant_number(suffix_list)
    # allow user to change suffix to a bigger number
    if new_suffix < available_suffix:
        new_suffix = available_suffix
    result = combine_name_suffix(new_name, new_suffix)
    return result


def ensure_unique_name(new_full_name: str, new_idx: int, name_list):
    '''Change <new_full_name> with blender style if re-name exists in <collection>, with time & space complexity O(n).
    
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
    # find a available suffix number. 0 means dont need suffix
    available_suffix = find_min_vacant_number(suffix_list)
    # allow user to change suffix to a bigger number
    if new_suffix < available_suffix:
        new_suffix = available_suffix
    result = combine_name_suffix(new_name, new_suffix)
    return result


def ensure_has_suffix(name: str, suffix: str):
    length = len(suffix)
    if name[-length:] != suffix:
        return ''.join((name, suffix))
    else:
        return name


def diff_ratio(str1: str, str2: str):
    '''Compare two strings' difference ratio, 1 means totally same and 0 means totally different.'''
    return difflib.SequenceMatcher(None, str1, str2).ratio()


def get_similar_str(example_str:str, str_list: list, tolerance=0.99):
    'Return the string which is most similar to the example_str and whose similar ratio is more than the 1 - tolerance in the str_list.'
    best_ratio = 0.0
    best_str = None
    for i in range(len(str_list)):
        ratio = difflib.SequenceMatcher(None, example_str, str_list[i]).ratio()
        if ratio > best_ratio and ratio > 1 - tolerance:
            best_str = str_list[i]
            best_ratio = ratio
    return best_str


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