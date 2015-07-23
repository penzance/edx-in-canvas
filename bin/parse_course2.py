import argparse
import json
import os
import tarfile
from xml.etree import ElementTree

def main():
    parser = argparse.ArgumentParser(description='Parse and upload an exported edX course.')
    parser.add_argument(
        'tar_file', type=argparse.FileType('r'),
        help='The .tgz file containing the exported edX course.'
    )
    args = parser.parse_args()
    print "Tarfile: {}".format(args.tar_file)

    tar = tarfile.open(fileobj=args.tar_file)
    parser = EdXMLParser(tar)
    upload_course(parser)


def upload_course(parser):
    data = dict(
        title=parser.get_course()['display_name'],
        org=parser.org,
        course=parser.course,
        run=parser.url_name,
        key_version=1,
        body=parser.get_course()
    )
    print json.dumps(data, indent=4)


class EdXMLParser:
    def __init__(self, tar):
        self.tar = tar
        self.parsed_course = None

    def get_course(self):
        if not self.parsed_course:
            self._parse_course()
        return self.parsed_course

    def _parse_course_xml(self):
        self.file_root = self.tar.getmembers()[0].name
        course_xml = self.tar.extractfile(
            "{}/course.xml".format(self.file_root)
        )
        content = ElementTree.parse(course_xml).getroot()
        self.org = content.attrib.get('org')
        self.course = content.attrib.get('course')
        self.url_name = content.attrib.get('url_name')

    def _populate_attributes(self, root, parent_id):
        content = {'type': root.tag}
        if parent_id:
            content['parent'] = parent_id
        for attr in root.attrib:
            content[attr] = root.attrib.get(attr)
        return content

    def _parse_structure(self, label, instance_id, parent_id=None):
        print "Parsing {} {}".format(label, instance_id)
        file_name = "{}/{}/{}.xml".format(self.file_root, label, instance_id)
        tar_element = self.tar.extractfile(file_name)
        root = ElementTree.parse(tar_element).getroot()
        content = self._populate_attributes(root, parent_id)
        if instance_id:
            usage_id = self._calculate_usage_id(instance_id, label)
            content['id'] = instance_id
            content['usage_id'] = usage_id

        for child in root:
            child_parser = getattr(EdXMLParser, '_parse_' + child.tag)
            # child_parser = inspect.getmembers(self)['_parse_' + child.tag]
            content['children'] = content.get('children', [])
            content['children'].append(child_parser(self, child, instance_id))
        return content

    def _calculate_usage_id(self, instance_id, label):
        # return "i4x:;_;_{};_{};_{}".format(self.usage_prefix.replace('/', ';_'), label, instance_id)
        return "block-v1:{}+{}+{}+type@{}+block@{}".format(
            self.org,
            self.course,
            self.url_name,
            label,
            instance_id
        )

    def _parse_course(self):
        self._parse_course_xml()
        self.parsed_course = self._parse_structure('course', self.url_name)

    def _parse_chapter(self, element, parent_id):
        instance_id = element.attrib.get('url_name')
        return self._parse_structure('chapter', instance_id=instance_id, parent_id=parent_id)

    def _parse_sequential(self, element, parent_id):
        instance_id = element.attrib.get('url_name')
        return self._parse_structure('sequential', instance_id=instance_id, parent_id=parent_id)

    def _parse_vertical(self, element, parent_id):
        instance_id = element.attrib.get('url_name')
        return self._parse_structure('vertical', instance_id=instance_id, parent_id=parent_id)

    def _parse_video(self, element, parent_id):
        instance_id = element.attrib.get('url_name')
        return self._parse_structure('video', instance_id=instance_id, parent_id=parent_id)

    def _parse_source(self, element, parent_id):
        content = self._populate_attributes(element, parent_id)
        content['id'] = element.attrib.get('url_name')
        content['usage_id'] = self._calculate_usage_id(content['id'], 'source')
        return content

    def _parse_video_asset(self, element, parent_id):
        content = self._populate_attributes(element, parent_id)
        video_content = []
        for child in element:
            video_content.append(self._populate_attributes(child, parent_id))
        content['children'] = video_content
        return content

    def _parse_html(self, element, parent_id):
        instance_id = element.attrib.get('url_name')
        file_name = "{}/html/{}.xml".format(self.file_root, instance_id)
        tar_element = self.tar.extractfile(file_name)
        root = ElementTree.parse(tar_element).getroot()
        content = self._populate_attributes(root, parent_id)
        file_name = "{}/html/{}.html".format(self.file_root, instance_id)
        html_file = self.tar.extractfile(file_name)
        content['id'] = instance_id
        content['usage_id'] = self._calculate_usage_id(content['id'], 'html')
        content['body'] = html_file.read()
        html_file.close()

        return content

    def _parse_problem(self, element, parent_id):
        # print "Display name: {}".format(element.attrib.get('display_name'))
        if element.attrib.get('display_name'):
            content = self._populate_attributes(element, parent_id)
        else:
            instance_id = element.attrib.get('url_name')
            file_name = "{}/problem/{}.xml".format(self.file_root, instance_id)
            tar_element = self.tar.extractfile(file_name)
            root = ElementTree.parse(tar_element).getroot()
            content = self._populate_attributes(root, parent_id)
            content['id'] = instance_id
            content['usage_id'] = self._calculate_usage_id(content['id'], 'problem')
        return content

    def _parse_discussion(self, element, parent_id):
        content = self._populate_attributes(element, parent_id)
        content['id'] = element.attrib.get('url_name')
        content['usage_id'] = self._calculate_usage_id(content['id'], 'discussion')
        return content

    def _parse_combinedopenended(self, element, parent_id):
        content = self._populate_attributes(element, parent_id)
        content['id'] = element.attrib.get('url_name')
        content['usage_id'] = self._calculate_usage_id(content['id'], 'combinedopenended')
        return content

    def _parse_annotatable(self, element, parent_id):
        instance_id = element.attrib.get('url_name')
        file_name = "{}/annotatable/{}.xml".format(self.file_root, instance_id)
        html_file = self.tar.extractfile(file_name)
        annotatable = {
            'type': 'annotatable',
            'id': instance_id,
            'usage_id': self._calculate_usage_id(instance_id, 'annotatable'),
            'parent': parent_id,
            'body': html_file.read()
        }
        html_file.close()
        return annotatable

    def _parse_wiki(self, element, parent_id):
        content = self._populate_attributes(element, parent_id)
        content['id'] = element.attrib.get('url_name')
        content['usage_id'] = self._calculate_usage_id(content['id'], 'wiki')
        return content

    def _parse_openassessment(self, element, parent_id):
        content = self._populate_attributes(element, parent_id)
        content['id'] = element.attrib.get('url_name')
        content['usage_id'] = self._calculate_usage_id(content['id'], 'openassessment')
        return content

    def _parse_poll_question(self, element, parent_id):
        content = self._populate_attributes(element, parent_id)
        content['id'] = element.attrib.get('url_name')
        content['usage_id'] = self._calculate_usage_id(content['id'], 'poll')
        return content

    def _parse_textannotation(self, element, parent_id):
        content = self._populate_attributes(element, parent_id)
        content['id'] = element.attrib.get('url_name')
        content['usage_id'] = self._calculate_usage_id(content['id'], 'textannotation')
        return content

main()