$(document).ajaxError(function (event, request, settings) {
    location.reload();
});

$(document).ready(function () {
    $('#populate_progress_bar').hide()
    initializeEdxCourseSelector();
    var data = $("#canvas_structure").data('canvas');
    populateCanvasCourse(data, data.length > 0 ? data[0].id : null, true);
    $("#edx_structure").removeAttr("data-edx");
    $("#canvas_structure").removeAttr("data-canvas");
    initializeAutopopulation()
});

function initializeEdxCourseSelector() {
    $('#edx_class_selector li').on('click', function () {
        var data = {edx_course_id: $(this).data("id")};
        $.get("/lti_tools/edx2canvas/edx_course", data).done(
            function (data) {
                var dropdownText = data['display_name'];
                dropdownText = dropdownText.length > 35 ? dropdownText.substr(0, 34) + '...' : dropdownText;
                $("#edx_dropdown_button").text(dropdownText);
                populateEdxCourse(data)
            });
    });
}

function populateEdxCourse(data) {
    $("#edx_structure").empty();
    $("#edx_structure").data('course_id', data.id);
    var context = {course_id: data.id, children: data.children};
    $("#edx_structure").html(Handlebars.compile($("#edx-panel-group-template").html())(context));
    intializeEdxDragging(data);
    initializeNavigation()
}

function populateCanvasCourse(data, selected, padEmpty) {
    $("#canvas_structure").empty();
    if (padEmpty) {
        for (var idx in data['modules']) {
            var module = data['modules'][idx];
            if (module.items.length == 0) {
                module.items.push({id: 0, title: 'Drag edX content here.'})
            }
        }
    }
    var context = {modules: data['modules']};
    $("#canvas_structure").html(Handlebars.compile($("#canvas-panel-group-template").html())(context));
    $("#canvas_structure").data('course_id', data['id']);
    if (selected != null) {
        $(selected).addClass("in")
    }
    intializeCanvasDragging(data['modules'])
}

function intializeEdxDragging(data) {
    for (section_idx in data.children) {
        var section = data.children[section_idx];
        if (section.id != null) {
            Sortable.create($("#fromList" + section.id)[0], edXSortableParams());
            for (subsection_idx in section.children) {
                var subsection = section.children[subsection_idx];
                Sortable.create($("#subsectionFromList" + subsection.id)[0], edXSortableParams());
                for (unit_idx in subsection.children) {
                    var unit = subsection.children[unit_idx];
                    Sortable.create($("#unitFromList" + unit.id)[0], edXSortableParams());
                    for (component_id in unit.children) {
                        var component = unit.children[component_id];
                        Sortable.create($("#componentFromList" + component.id)[0], edXSortableParams())
                    }
                }
            }
        }
    }
}

function edXSortableParams() {
    return {
        group: {name: 'modulegroup', pull: 'clone', put: false},
        sort: false,
        animation: 150
    }
}

function intializeCanvasDragging(data) {
    for (x in data) {
        var module = data[x];
        Sortable.create($("#toList" + module.id)[0], canvasSortableParams())
    }
}

function canvasSortableParams() {
    return {
        group: {name: 'modulegroup', pull: false, put: true},
        sort: false,
        animation: 150,
        onAdd: function (evt) {
            moduleDragged(evt)
        }
    }
}

function initializeNavigation() {
    $(".subsection_expand").on('click', function (e) {
        clearNavHighlight();
        $(".nav_unit").hide();
        $(".nav_component").hide();
        unit = $(this).parent().parent();
        unit.children(".nav_unit").slideDown();
        updateLtiFrame(unit);
        unit.addClass('highlighted_element')
    });
    $(".unit_expand").on('click', function (e) {
        clearNavHighlight();
        $(".nav_component").hide();
        component = $(this).parent().parent();
        component.children(".nav_component").slideDown();
        updateLtiFrame(component);
        component.addClass('highlighted_element')
    });
    $(".component_expand").on('click', function (e) {
        clearNavHighlight();
        component = $(this).parent().parent();
        updateLtiFrame(component);
        component.addClass('highlighted_element')
    });
    $(".nav_unit").hide();
    $(".nav_component").hide()
}

function clearNavHighlight() {
    $(".nav_subsection").removeClass('highlighted_element');
    $(".nav_unit").removeClass('highlighted_element');
    $(".nav_component").removeClass('highlighted_element')
}


function updateLtiFrame(element) {
    var usage_id = encodeURIComponent(element.data("usage_id"));
    var course_id = encodeURIComponent(element.data("course_id"));
    console.log("Usage: " + usage_id + ", course: " + course_id);
    $("#lti_iframe").addClass("lti_iframe_expanded");
    $("#lti_iframe").attr("src", "/lti_tools/edx2canvas/lti_preview?usage_id=" + usage_id + "&course_id=" + course_id)
}

function moduleDragged(evt) {
    var selected = "#collapse" + $(evt.to).parent().data("module_id");
    var data = {
        usage_id: $(evt.item).data("usage_id"),
        module_id: $(evt.to).data("id"),
        edx_course_id: $(evt.item).data("course_id"),
        canvas_course_id: $('#canvas_structure').data('course_id'),
        title: $(evt.item).data("title"),
        position: evt.newIndex + 1,
        graded: $(evt.item).data("type") == "problem",
        points: $(evt.item).data("points")
    };
    evt.item.innerText = "Adding to Canvas...";
    $.post("/lti_tools/edx2canvas/add_to_canvas", data).done(
        function (data) {
            populateCanvasCourse(data, selected, true)
        });
}

function addToCanvas(data) {
    $.post("/lti_tools/edx2canvas/add_to_canvas", data).done(
        function (data) {
            populateCanvasCourse(data, null, true)
        });
}

function initializeAutopopulation() {
    $('#autopopulate_modal_instructions').html($("#autopopulate_overview").html())
    $('#auto_populate_button').on('click', function () {
        var createAssignments = $("#create_assignments").is(':checked')
        console.log("Populating. Creating assignments: " + createAssignments);
        var granularity = $("#autopopulate_granularity").find(".selected_granularity").prop('value')
        if (granularity != undefined) {
            autoPopulate(".nav_" + granularity, createAssignments)
        }
    })
    $("#autopopulate_granularity").find(".btn").on('click', function () {
        $(this).parent().parent().find(".btn").removeClass('selected_granularity')
        $(this).addClass('selected_granularity')
        var instructions = "#autopopulate_" + $(this).prop('value')
        $('#autopopulate_modal_instructions').html($(instructions).html())
    })
}

function autoPopulate(leafSelector, createAssignments) {
    totalCalls = 0;
    $('.edx-panel').each(function () {
        var name = $(this).find('a').html().trim();
        if (name != null && name.length > 0) {
            totalCalls++;
            $(this).find(leafSelector).each(function () {
                totalCalls++
            })
        }
    });
    callsMade = 0;
    $('#button_bar').hide()
    var progress = $('#populate_progress_bar')
    progress.show()

    var position = 0
    $('.edx-panel').each(function () {
        var name = $(this).find('a').html().trim();
        if (name != null && name.length > 0) {
            var module_data = {
                canvas_course_id: $('#canvas_structure').data('course_id'),
                module_name: $(this).find('a').html().trim(),
                position: position++
            };
            $.ajax({
                type: "POST",
                url: "/lti_tools/edx2canvas/create_canvas_module",
                data: module_data,
                success: autoPopulateChildren($(this), leafSelector, createAssignments)
            });
        }
    })
}

function autoPopulateChildren(parent, leafSelector, createAssignments) {
    return function (response) {
        updateProcess();
        populateCanvasCourse(response, null, true);
        var module_id = response.module_id;
        var position = 0;
        parent.find(leafSelector).each(function () {
            if (filterElement($(this).data("type"))) {
                updateProcess()
            } else {
                var module_item_data = {
                    usage_id: $(this).data("usage_id"),
                    module_id: module_id,
                    edx_course_id: $(this).data("course_id"),
                    canvas_course_id: $('#canvas_structure').data('course_id'),
                    title: $(this).data('title'),
                    position: position++,
                    graded: $(this).data("points") != 0 && createAssignments,
                    points: $(this).data("points")
                };
                $.post("/lti_tools/edx2canvas/add_to_canvas", module_item_data).done(
                    function (response) {
                        updateProcess()
                        populateCanvasCourse(response, '.canvas-collapse', false);
                    });
            }
        })
    }
}

function filterElement(type) {
    return type == 'discussion'
}

function updateProcess() {
    callsMade++;
    var percentage = callsMade / totalCalls * 100
    $('#progress-bar').css('width', percentage + "%")
    if (callsMade == totalCalls) {
        $('#populate_progress_bar').hide()
        $('#button_bar').show()
    }
}