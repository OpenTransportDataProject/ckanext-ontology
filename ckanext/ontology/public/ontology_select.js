ckan.module('ontology_select', function ($, _) {
  return {
    initialize: function () {
      var self = this;

      if (this.options.value.id) {
        this.init();
      }

      $('#'+this.options.ontology).on('change', function (e) {
        self.populateNodes(this.value);
      });

      $('#'+this.options.delete).change(function() {
        $(self.el).remove();
      });
    },

    populateNodes: function(ontologyId) {
      for (i = 0; i < this.options.ontologies.length; i++) {
        if (this.options.ontologies[i].id === ontologyId) {
          this.addOptions(this.options.ontologies[i].nodes);
        }
      }
    },

    addOptions: function(nodes) {
      for (i = 0; i < nodes.length; i++) {
        $('#'+this.options.node).append($('<option>', {
          value: nodes[i].id,
          text: nodes[i].name
        }));
      }
    },

    init: function() {
      for (i = 0; i < this.options.ontologies.length; i++) {
        if (this.options.ontologies[i].id === this.options.value.ontology_id) {
          this.addOptions(this.options.ontologies[i].nodes);
        }
      }
      $('#'+this.options.ontology + ' option[value=' + this.options.value.ontology_id + ']').prop('selected', true);
      $('#'+this.options.node + ' option[value=' + this.options.value.node_id + ']').prop('selected', true);
    }
  };
});
