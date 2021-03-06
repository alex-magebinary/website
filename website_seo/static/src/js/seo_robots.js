// Override necessary parts of website/static/src/js/website.seo.js to enable
// META robots management via promote panel.
//
// We need to override all needed function. We can't use the super function
// here.

(function () {
    'use strict';

    var website = openerp.website;
    var _t = openerp._t;

    website.add_template_file('/website_seo/static/src/xml/website_seo_robots.xml');

    website.seo.HtmlPage.include({
        robots: function() {
            var $robots = $('meta[name=robots]');
            return ($robots.length > 0) && ($robots.attr('content') && $robots.attr('content').trim());
        },
        changeRobots: function(robots) {
            $('meta[name=robots]').attr('content', robots);
            this.trigger('robots-changed', robots);
        },
        seo_url: function () {
            var $seo_url = $('meta[name=seo_url]');
            return ($seo_url.length > 0) && ($seo_url.attr('content') && $seo_url.attr('content').trim());
        },
        changeSeoUrl: function (seo_url) {
            $('meta[name=seo_url]').attr('content', seo_url);
            this.trigger('seo_url-changed', seo_url);
        },
    });

    // This replaces \b, because accents(e.g. à, é) are not seen as word boundaries.
    // Javascript \b is not unicode aware, and words beginning or ending by accents won't match \b
    var WORD_SEPARATORS_REGEX = '([\\u2000-\\u206F\\u2E00-\\u2E7F\'!"#\\$%&\\(\\)\\*\\+,\\-\\.\\/:;<=>\\?¿¡@\\[\\]\\^_`\\{\\|\\}~\\s]+|^|$)';

    function analyzeKeyword(htmlPage, keyword) {
        return  htmlPage.isInTitle(keyword) ? {
                    title: 'label label-primary',
                    description: "This keyword is used in the page title",
                } : htmlPage.isInDescription(keyword) ? {
                    title: 'label label-info',
                    description: "This keyword is used in the page description",
                } : htmlPage.isInBody(keyword) ? {
                    title: 'label label-info',
                    description: "This keyword is used in the page content."
                } : {
                    title: 'label label-default',
                    description: "This keyword is not used anywhere on the page."
                };
    }

    website.seo.Suggestion = openerp.Widget.extend({
        template: 'website.seo_suggestion',
        events: {
            'click .js_seo_suggestion': 'select',
        },
        init: function (parent, options) {
            this.root = options.root;
            this.keyword = options.keyword;
            this.language = options.language;
            this.htmlPage = options.page;
            this._super(parent);
        },
        start: function () {
            this.htmlPage.on('title-changed', this, this.renderElement);
            this.htmlPage.on('description-changed', this, this.renderElement);
        },
        analyze: function () {
            return analyzeKeyword(this.htmlPage, this.keyword);
        },
        highlight: function () {
            return this.analyze().title;
        },
        tooltip: function () {
            return this.analyze().description;
        },
        select: function () {
            this.trigger('selected', this.keyword);
        },
    });

    website.seo.SuggestionList = openerp.Widget.extend({
        template: 'website.seo_suggestion_list',
        init: function (parent, options) {
            this.root = options.root;
            this.language = options.language;
            this.htmlPage = options.page;
            this._super(parent);
        },
        start: function () {
            this.refresh();
        },
        refresh: function () {
            var self = this;
            self.$el.append(_t("Loading..."));
            var language = self.language || website.get_context().lang.toLowerCase();
            openerp.jsonRpc('/website/seo_suggest', 'call', {
                'keywords': self.root,
                'lang': language,
            }).then(function(keyword_list){
                self.addSuggestions(keyword_list);
            });
        },
        addSuggestions: function(keywords) {
            var self = this;
            self.$el.empty();
            // TODO Improve algorithm + Ajust based on custom user keywords
            var regex = new RegExp(self.root, "gi");
            var keywords = _.map(_.uniq(keywords), function (word) {
                return word.replace(regex, "").trim();
            });
            // TODO Order properly ?
            _.each(keywords, function (keyword) {
                if (keyword) {
                    var suggestion = new website.seo.Suggestion(self, {
                        root: self.root,
                        language: self.language,
                        keyword: keyword,
                        page: self.htmlPage,
                    });
                    suggestion.on('selected', self, function (word, language) {
                        self.trigger('selected', word, language);
                    });
                    suggestion.appendTo(self.$el);
                }
            });
        },
    });

    website.seo.Keyword = openerp.Widget.extend({
        template: 'website.seo_keyword',
        events: {
            'click a[data-action=remove-keyword]': 'destroy',
        },
        maxWordsPerKeyword: 4, // TODO Check
        init: function (parent, options) {
            this.keyword = options.word;
            this.language = options.language;
            this.htmlPage = options.page;
            this._super(parent);
        },
        start: function () {
            this.htmlPage.on('title-changed', this, this.updateLabel);
            this.htmlPage.on('description-changed', this, this.updateLabel);
            this.suggestionList = new website.seo.SuggestionList(this, {
                root: this.keyword,
                language: this.language,
                page: this.htmlPage,
            });
            this.suggestionList.on('selected', this, function (word, language) {
                this.trigger('selected', word, language);
            });
            this.suggestionList.appendTo(this.$('.js_seo_keyword_suggestion'));
        },
        analyze: function () {
            return analyzeKeyword(this.htmlPage, this.keyword);
        },
        highlight: function () {
            return this.analyze().title;
        },
        tooltip: function () {
            return this.analyze().description;
        },
        updateLabel: function () {
            var cssClass = "oe_seo_keyword js_seo_keyword " + this.highlight();
            this.$(".js_seo_keyword").attr('class', cssClass);
            this.$(".js_seo_keyword").attr('title', this.tooltip());
        },
        destroy: function () {
            this.trigger('removed');
            this._super();
        },
    });

    website.seo.KeywordList = openerp.Widget.extend({
        template: 'website.seo_list',
        maxKeywords: 10,
        init: function (parent, options) {
            this.htmlPage = options.page;
            this._super(parent);
        },
        start: function () {
            var self = this;
            var existingKeywords = self.htmlPage.keywords();
            if (existingKeywords.length > 0) {
                _.each(existingKeywords, function (word) {
                    self.add.call(self, word);
                });
            } else {
                var companyName = self.htmlPage.company().toLowerCase();
                if (companyName != 'yourcompany') {
                    self.add(companyName);
                }
            }
        },
        keywords: function () {
            var result = [];
            this.$('.js_seo_keyword').each(function () {
                result.push($(this).data('keyword'));
            });
            return result;
        },
        isFull: function () {
            return this.keywords().length >= this.maxKeywords;
        },
        exists: function (word) {
            return _.contains(this.keywords(), word);
        },
        add: function (candidate, language) {
            var self = this;
            // TODO Refine
            var word = candidate ? candidate.replace(/[,;.:<>]+/g, " ").replace(/ +/g, " ").trim().toLowerCase() : "";
            if (word && !self.isFull() && !self.exists(word)) {
                var keyword = new website.seo.Keyword(self, {
                    word: word,
                    language: language,
                    page: this.htmlPage,
                });
                keyword.on('removed', self, function () {
                   self.trigger('list-not-full');
                   self.trigger('removed', word);
                });
                keyword.on('selected', self, function (word, language) {
                    self.trigger('selected', word, language);
                });
                keyword.appendTo(self.$el);
            }
            if (self.isFull()) {
                self.trigger('list-full');
            }
        },
    });

    website.seo.Configurator.include({
        events: {
            'keyup input[name=seo_page_keywords]': 'confirmKeyword',
            'keyup input[name=seo_page_title]': 'titleChanged',
            'keyup textarea[name=seo_page_description]': 'descriptionChanged',
            'change select[name=seo_page_robots]': 'robotsChanged',
            'keyup input[name=seo_url]': 'seoUrlChanged',
            'click button[data-action=add]': 'addKeyword',
            'click button[data-action=update]': 'update',
            'change select[name=seo_url_page_language]': 'changeLanguage',
            'hidden.bs.modal': 'destroy'
        },
        canEditRobots: false,
        canEditSeoUrl: false,
        start: function() {
            var self = this;
            var $modal = self.$el;
            var htmlPage = this.htmlPage = new website.seo.HtmlPage();
            $modal.find('.js_seo_page_url').text(htmlPage.url());
            $modal.find('input[name=seo_page_title]').val(htmlPage.title());
            $modal.find('textarea[name=seo_page_description]').val(htmlPage.description());
            $modal.find('select[name=seo_page_robots]').val(htmlPage.robots());
            $modal.find('input[name=seo_url]').val(htmlPage.seo_url());

            var url_parts = window.location.href.split('/');
            var path = url_parts[url_parts.length - 1];
            if (path) {
                path = path.replace('#', '').replace('?', '');
            }
            if (! path || path === 'homepage'){
                $('input[name=seo_url]').css('visibility','hidden');
                $('label[for=seo_url]').css('visibility','hidden');
            }
            self.known_urls = [];
            website.session.model('website.seo.metadata')
                .call('get_known_seo_urls')
                .then(function(data) {
                    self.known_urls = data;
                });
            self.keywordList = new website.seo.KeywordList(self, { page: htmlPage });
            self.keywordList.on('list-full', self, function () {
                $modal.find('input[name=seo_page_keywords]')
                    .attr('readonly', "readonly")
                    .attr('placeholder', "Remove a keyword first");
                $modal.find('button[data-action=add]')
                    .prop('disabled', true).addClass('disabled');
            });
            self.keywordList.on('list-not-full', self, function () {
                $modal.find('input[name=seo_page_keywords]')
                    .removeAttr('readonly').attr('placeholder', "");
                $modal.find('button[data-action=add]')
                    .prop('disabled', false).removeClass('disabled');
            });
            self.keywordList.on('selected', self, function (word, language) {
                self.keywordList.add(word, language);
            });
            self.keywordList.appendTo($modal.find('.js_seo_keywords_list'));
            self.disableUnsavableFields();
            self.renderPreview();
            $modal.modal();
            self.getLanguages();
        },
        getLanguages: function(){
            var self = this;
            openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'website',
                method: 'get_languages',
                args: [],
                kwargs: {
                    ids: [website.get_context().website_id],
                    context: website.get_context()
                }
            }).then( function(data) {
                self.$('#language-box').html(openerp.qweb.render('Configurator.language_promote', {
                    'language': data,
                    'def_lang': website.get_context().lang
                }));
                self.$('#seo-language-box').html(openerp.qweb.render('Configurator.language_promote', {
                    'language': data,
                    'def_lang': website.get_context().lang
                }));
            });
        },
        disableUnsavableFields: function () {
            var self = this;
            var $modal = self.$el;
            self.loadMetaData().then(function(data) {
                self.canEditTitle = data && ('website_meta_title' in data);
                self.canEditDescription = data && ('website_meta_description' in data);
                self.canEditKeywords = data && ('website_meta_keywords' in data);
                // Allow editing the meta robots only for pages that have
                self.canEditRobots = data && ('website_meta_robots' in data);
                self.canEditSeoUrl = data && ('seo_url' in data);
                if (!self.canEditTitle) {
                    $modal.find('input[name=seo_page_title]').attr('disabled', true);
                }
                if (!self.canEditDescription) {
                    $modal.find('textarea[name=seo_page_description]').attr('disabled', true);
                }
                if (!self.canEditTitle && !self.canEditDescription && !self.canEditKeywords) {
                    $modal.find('button[data-action=update]').attr('disabled', true);
                }
                if (!self.canEditRobots) {
                    $modal.find('select[name=seo_page_robots]').attr('disabled', true);
                }
                if (!self.canEditSeoUrl) {
                    $modal.find('input[name=seo_url]').attr('disabled', true);
                }
            });
        },
        suggestField: function (field) {
            var tip = self.$('.js_seo_' + field + '_tips');
            if (tip.children().length === 0) {
                var model = website.session.model('website.seo.metadata');
                model.call('get_information_from', [field, website.get_context()]).then(function(data) {
                    if (data.length){
                        new website.seo.Tip(self, {
                            message: data,
                            type: 'info'
                        }).appendTo(tip);
                    }
                });
            }
            else {
                tip.children()[0].remove();
            }
        },
        addKeyword: function (word) {
            var $input = this.$('input[name=seo_page_keywords]');
            var $language = this.$('select[name=seo_page_language]');
            var keyword = _.isString(word) ? word : $input.val();
            var language = $language.val().toLowerCase();
            this.keywordList.add(keyword, language);
            $input.val("");
        },
        update: function () {
            var self = this;
            var data = {};
            var error = null;
            if (self.canEditTitle) {
                data.website_meta_title = this.$('input[name=seo_page_title]').val(); //self.htmlPage.title();
            }
            if (self.canEditDescription) {
                data.website_meta_description = this.$('textarea[name=seo_page_description]').val(); //self.htmlPage.description();
            }
            if (self.canEditKeywords) {
                data.website_meta_keywords = self.keywordList.keywords().join(", ");
            }
            if (self.canEditRobots) {
                data.website_meta_robots = this.$('select[name=seo_page_robots]').val(); //self.htmlPage.robots();
            }
            if (self.canEditSeoUrl) {
                var seo_url_regex = /^([.a-zA-Z0-9-_]+)$/;
                var seo_url = this.$('input[name=seo_url]').val(); //self.htmlPage.seo_url();

                if (seo_url && !error && !seo_url.match(seo_url_regex)) {
                    error = _t("Invalid SEO URL. The allowed characters are a-z, A-Z, 0-9, - and _.");
                }
                if (!error && self.known_urls.indexOf(seo_url) >= 0) {
                    error = _.str.sprintf(_t("The SEO URL '%s' is already taken in the application."), seo_url);
                }
                if (error) {
                    var div_error = self.$('.js_seo_url_tips');
                    if (div_error.children().length > 0) {
                        div_error.children()[0].remove();
                    }
                    new website.seo.Tip(self, {message: error, type: 'danger'}).appendTo(div_error);
                }
                else {
                    data.seo_url = seo_url;
                }
            }
            if (!error) {
                self.saveMetaData(data).then(function() {
                    self.$el.modal('hide');
                    self.$('#seo-language-box').val(website.get_context().lang);
                    self.getSeoPath().then(function(seo_path) {
                        if (seo_path) {
                            location.replace(seo_path, 301);
                        }
                    });
                });
            }
        },
        getSeoPath: function () {
            var self = this;
            var obj = this.getMainObject();
            var def = $.Deferred();
            if (!obj) {
                def.resolve(null);
            } else {
                var ctx = website.get_context();
                var lang = self.getCurrentLanguage();
                if (lang) {
                    ctx.lang = lang;
                }
                website.session.model(obj.model)
                    .call('get_seo_path', [obj.id, ctx])
                    .then(function (result) {
                        if (result && result[0] !== false) {
                            def.resolve(result[0]);
                        } else {
                            def.resolve(null);
                        }
                    }).fail(function () {
                        def.reject();
                    });
            }
            return def;
        },
        loadMetaData: function () {
            var self = this;
            var obj = this.getMainObject();
            var def = $.Deferred();
            if (!obj) {
                def.resolve(null);
            } else {
                var ctx = website.get_context();
                var lang = self.getCurrentLanguage();
                if (lang) {
                    ctx.lang = lang;
                }
                var fields = ['website_meta_title', 'website_meta_description', 'website_meta_keywords', 'website_meta_robots', 'seo_url'];
                var model = website.session.model(obj.model);
                model.call('read', [[obj.id], fields, ctx]).then(function(data) {
                    if (data.length) {
                        var meta = data[0];
                        meta.model = obj.model;
                        def.resolve(meta);
                    } else {
                        def.resolve(null);
                    }
                }).fail(function() {
                        def.reject();
                });
            }
            return def;
        },
        saveMetaData: function (data) {
            var obj = this.getMainObject();
            if (!obj) {
                return $.Deferred().reject();
            } else {
                var ctx = website.get_context();
                var lang = this.getCurrentLanguage();
                if (lang) {
                    ctx.lang = lang;
                }
                return website.session.model(obj.model).call('write', [[obj.id], data, ctx]);
            }
        },
        robotsChanged: function () {
            var self = this;
            setTimeout(function () {
                var robots = self.$('select[name=seo_page_robots]').val();
                self.htmlPage.changeRobots(robots);
                self.renderPreview();
            }, 0);
        },
        seoUrlChanged: function () {
            var self = this;
            setTimeout(function () {
                var seo_url = self.$('input[name=seo_url]').val();
                self.htmlPage.changeSeoUrl(seo_url);
                self.renderPreview();
            }, 0);
        },
        renderPreview: function () {
            var self = this;
            var url = this.htmlPage.url();
            var seo_url = this.$('input[name=seo_url]').val();
            self.getSeoPath().then(function(seo_path) {
                if (seo_url) {
                    var url_parts = url.split('/');
                    var lang = self.getCurrentLanguage();
                    if (seo_path) {
                        if (lang && lang !== website.get_context().lang) {
                            url_parts.splice(3, 0, lang);
                        }
                        url_parts[url_parts.length - 1] = seo_url;
                    }
                    else {
                        url_parts = url_parts.slice(0, 3);
                        if (lang && lang !== website.get_context().lang) {
                            url_parts.push(lang);
                        }
                        url_parts.push(seo_url);
                    }
                    url = url_parts.join('/');
                }
                var preview = new website.seo.Preview(self, {
                    title: self.htmlPage.title(),
                    description: self.htmlPage.description(),
                    url: url,
                });
                var $preview = self.$('.js_seo_preview');
                $preview.empty();
                preview.appendTo($preview);
            });
        },
        getCurrentLanguage: function () {
            return this.$('#seo-language-box').val();
        },
        changeLanguage: function() {
            var self = this;
            this.loadMetaData().then(function(data){
                var $modal = self.$el;
                $modal.find('input[name=seo_page_title]').val(data.website_meta_title);
                $modal.find('textarea[name=seo_page_description]').val(data.website_meta_description || '');
                $modal.find('select[name=seo_page_robots]').val(data.website_meta_robots);
                $modal.find('input[name=seo_url]').val(data.seo_url || '');
                self.renderPreview();
            });
        }
    });

    website.ready().done(function() {
        $(document.body).on('click', '#title_tip', function() {
            new website.seo.Configurator(this).suggestField('website_meta_title');
        });
        $(document.body).on('click', '#description_tip', function() {
            new website.seo.Configurator(this).suggestField('website_meta_description');
        });
    });

})();
