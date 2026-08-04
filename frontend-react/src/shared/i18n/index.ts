import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

const enCommon = {
  app_title: 'FastAPI Tenant Workspace',
  welcome: 'Welcome to your Workspace',
  common: {
    loading: 'Loading...',
    save: 'Save',
    cancel: 'Cancel',
    delete: 'Delete',
    edit: 'Edit',
    search: 'Search',
    actions: 'Actions',
    status: 'Status',
    created_at: 'Created At',
    offline_warning: 'You are currently offline. Check your internet connection.',
  },
  auth: {
    login: 'Log In',
    register: 'Create Account',
    logout: 'Log Out',
    session_expired: 'Your session has expired. Please log in again.',
  },
  organizations: {
    title: 'Organizations',
    create: 'Create Organization',
    select: 'Select Organization',
    no_org: 'No organization selected',
  },
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: enCommon },
    },
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false,
    },
  });

export default i18n;
