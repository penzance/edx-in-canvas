import argparse
import json
import os
from xml.etree import ElementTree

from django.core.management.base import BaseCommand, CommandError

from edx2canvas import models

class Command(BaseCommand):
    help = 'Parse an expanded edX course directory'

    def add_arguments(self, parser):
        parser.add_argument(
            'course_xml', type=argparse.FileType('r'),
            help='The course.xml file at the root of the expanded edX course.'
        )

    def handle(self, *args, **options):
        directory = os.path.dirname(options['course_xml'].name)
        root = ElementTree.parse(options['course_xml']).getroot()
        course = models.EdxCourse(
            title='',
            org=root.attrib['org'],
            course=root.attrib['course'],
            run=root.attrib['url_name'],
            key_version=1
        )
        parsed_course = EdXMLParser(course, directory).get_course()
        self.annotate_points(parsed_course)
        course.title = parsed_course['display_name']
        course.save()
        parsed_course['id'] = course.id
        with open("courses/{}.json".format(course.course), 'w') as jsonfile:
            jsonfile.write(json.dumps(parsed_course, indent=4))

    def annotate_points(self, dictionary):
        if dictionary['type'] == 'problem':
            dictionary['points'] = 1
            return 1
        if 'children' not in dictionary:
            dictionary['points'] = 0
            return 0
        children_points = 0
        for child in dictionary['children']:
            children_points += self.annotate_points(child)
        dictionary['points'] = children_points
        return children_points

class EdXMLParser():
    def __init__(self, edx_course, directory):
        self.edx_course = edx_course
        self.parsed_course = None
        self.directory = directory
        self.course_id = edx_course.run
        self.course_path = edx_course.run
        self.usage_prefix = "{}/{}".format(edx_course.org, edx_course.course)

    def get_course(self):
        if not self.parsed_course:
            self._parse_course()
        return self.parsed_course

    def _populate_attributes(self, root, parent_id):
        content = {'type': root.tag}
        if parent_id:
            content['parent'] = parent_id
        for attr in root.attrib:
            content[attr] = root.attrib.get(attr)
        return content

    def _parse_structure(self, label, instance_id, parent_id=None):
        file_name = "{}/{}/{}.xml".format(self.directory, label, instance_id)
        root = ElementTree.parse(file_name).getroot()
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
            self.edx_course.org,
            self.edx_course.course,
            self.edx_course.run,
            label,
            instance_id
        )

    def _parse_course(self):
        self.parsed_course = self._parse_structure('course', self.course_id)
        self.parsed_course['id'] = self.edx_course.id

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
        root = ElementTree.parse("{}/html/{}.xml".format(self.directory, instance_id)).getroot()
        content = self._populate_attributes(root, parent_id)
        with open("{}/html/{}.html".format(self.directory, instance_id)) as html_file:
            content['id'] = instance_id
            content['usage_id'] = self._calculate_usage_id(content['id'], 'html')
            content['body'] = html_file.read()
        return content

    def _parse_problem(self, element, parent_id):
        # print "Display name: {}".format(element.attrib.get('display_name'))
        if element.attrib.get('display_name'):
            content = self._populate_attributes(element, parent_id)
        else:
            instance_id = element.attrib.get('url_name')
            file_name = "{}/problem/{}.xml".format(self.directory, instance_id)
            root = ElementTree.parse(file_name).getroot()
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
        with open("{}/annotatable/{}.xml".format(self.directory, instance_id)) as html_file:
            return {
                'type': 'annotatable',
                'id': instance_id,
                'usage_id': self._calculate_usage_id(instance_id, 'annotatable'),
                'parent': parent_id,
                'body': html_file.read()
            }

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
