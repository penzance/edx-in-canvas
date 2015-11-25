import argparse
import json
import os
import requests
import tempfile
from xml.etree import ElementTree

def main():
    parser = argparse.ArgumentParser(description='Parse and upload an exported edX course.')
    parser.add_argument(
        'tar_file', type=argparse.FileType('r'),
        help='The .tgz file containing the exported edX course.'
    )
    parser.add_argument(
        'url_base',
        help='Base of the server URL (eg "http://example.com/").'
    )
    args = parser.parse_args()

    tmp_dir = tempfile.mkdtemp()
    os.system("tar -zxf {} -C {}".format(args.tar_file.name, tmp_dir))
    root_dir = "{}/{}".format(tmp_dir, os.listdir(tmp_dir)[0])
    parser = EdXMLParser(root_dir)
    upload_course(parser, args.url_base)
    settings = """
    Edx course settings:
        Course Name:   {}
        Organization:  {}
        Course Number: {}
        CourseRun:     {}
    """.format(parser.get_course()['display_name'], parser.org, parser.course, parser.url_name)
    print settings


def check_scores(node):
    if 'children' not in node:
        return
    for child in node['children']:
        if 'score' not in child:
            print "No score in {}".format(child)
        check_scores(child)

def upload_course(parser, url_base):
    data = dict(
        title=parser.get_course()['display_name'],
        org=parser.org,
        course=parser.course,
        run=parser.url_name,
        key_version=1,
        body=json.dumps(parser.get_course())
    )
    url = "{}/edx2canvas/edx_course/new".format(url_base)
    headers = {'Content-Type': 'application/json'}
    r = requests.post(url, data=json.dumps(data), headers=headers)
    if r.status_code == 201:
        print "Successfully uploaded course {}".format(data['title'])
    else:
        print "Error uploading {}: {}".format(data['title'], r)

class EdXMLParser:
    def __init__(self, directory):
        self.parsed_course = None
        self.directory = directory

    def get_course(self):
        if not self.parsed_course:
            self._parse_course()
        return self.parsed_course

    def _populate_attributes(self, root, parent_id):
        content = {'type': root.tag, 'score': 0}
        if parent_id:
            content['parent'] = parent_id
        for attr in root.attrib:
            content[attr] = root.attrib.get(attr)
        return content

    def _parse_structure(self, label, instance_id, usage_id, parent_id=None):
        file_name = "{}/{}/{}.xml".format(self.directory, label, instance_id)
        root = ElementTree.parse(file_name).getroot()
        content = self._populate_attributes(root, parent_id)
        if instance_id:
            content['id'] = instance_id
            content['usage_id'] = usage_id

        for child in root:
            try:
                child_parser = getattr(EdXMLParser, '_parse_' + child.tag)
            except AttributeError:
                child_parser = getattr(EdXMLParser, '_parse_leaf')
            content['children'] = content.get('children', [])
            child = child_parser(self, child, instance_id, child.tag)
            content['children'].append(child)
            content['score'] = content['score'] + child['score']
        return content

    def _calculate_usage_id(self, instance_id, label):
        # This method returns a usage ID for a split-mongo installation. For
        # the mongo DB in the Devstack or Full Stack installations, use:
        # return "i4x:;_;_{};_{};_{}".format(self.usage_prefix.replace('/', ';_'), label, instance_id)
        return "block-v1:{}+{}+{}+type@{}+block@{}".format(
            self.org,
            self.course,
            self.url_name,
            label,
            instance_id
        )

    def _parse_course_xml(self):
        file_name = "{}/course.xml".format(self.directory)
        root = ElementTree.parse(file_name).getroot()
        self.url_name = root.attrib.get('url_name')
        self.course = root.attrib.get('course')
        self.org = root.attrib.get('org')

    def _parse_course(self):
        self._parse_course_xml()
        usage_id = self._calculate_usage_id(self.url_name, 'course')
        self.parsed_course = self._parse_structure('course', self.url_name, usage_id)

    def _parse_chapter(self, element, parent_id, tag):
        instance_id = self._get_instance_id(element)
        usage_id = self._calculate_usage_id(element.attrib.get('url_name'), tag)
        return self._parse_structure(tag, instance_id=instance_id, usage_id=usage_id, parent_id=parent_id)

    def _parse_sequential(self, element, parent_id, tag):
        instance_id = self._get_instance_id(element)
        usage_id = self._calculate_usage_id(element.attrib.get('url_name'), tag)
        return self._parse_structure(tag, instance_id=instance_id, usage_id=usage_id, parent_id=parent_id)

    def _parse_vertical(self, element, parent_id, tag):
        instance_id = self._get_instance_id(element)
        usage_id = self._calculate_usage_id(element.attrib.get('url_name'), tag)
        return self._parse_structure(tag, instance_id=instance_id, usage_id=usage_id, parent_id=parent_id)

    def _parse_problem(self, element, parent_id, tag):
        if element.attrib.get('display_name'):
            content = self._populate_attributes(element, parent_id)
            content['score'] = 1
        else:
            instance_id = self._get_instance_id(element)
            # instance_id = element.attrib.get('url_name')
            file_name = "{}/problem/{}.xml".format(self.directory, instance_id)
            root = ElementTree.parse(file_name).getroot()
            content = self._populate_attributes(root, parent_id)
            content['id'] = instance_id
            content['usage_id'] = self._calculate_usage_id(content['id'], tag)
            score = 0
            score += len(root.findall('.//coderesponse'))
            score += len(root.findall('.//choiceresponse'))
            score += len(root.findall('.//customresponse'))
            score += len(root.findall('.//formularesponse'))
            score += len(root.findall('.//imageresponse'))
            score += len(root.findall('.//jsmeresponse'))
            score += len(root.findall('.//multiplechoiceresponse'))
            score += len(root.findall('.//numericalresponse'))
            score += len(root.findall('.//optionresponse'))
            score += len(root.findall('.//schematicresponse'))
            score += len(root.findall('.//stringresponse'))
            content['score'] = score if score else 1
        return content

    def _parse_leaf(self, element, parent_id, tag):
        content = self._populate_attributes(element, parent_id)
        content['id'] = self._get_instance_id(element)
        content['usage_id'] = self._calculate_usage_id(element.attrib.get('url_name'), tag)
        return content

    def _get_instance_id(self, element):
        instance_id = element.attrib.get('url_name')
        if instance_id:
            instance_id = instance_id.replace('.', '_')
        return instance_id

main()
